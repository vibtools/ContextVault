"""End-to-end browser extraction and archive export workflow."""

from __future__ import annotations

import concurrent.futures
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.browser.session_worker import BrowserSessionWorker
from src.core.archive_builder import ArchiveBuilder
from src.core.task_manager import TaskContext
from src.models.conversation import ConversationListItem
from src.models.settings import ApplicationSettings
from src.models.tasks import EventType
from src.parsers.conversation_parser import ConversationParser

LOGGER = logging.getLogger(__name__)


class ExportPipeline:
    """Coordinate browser loading, parsing, assets, and frozen archive generation."""

    def __init__(self, browser_worker: BrowserSessionWorker) -> None:
        self._browser_worker = browser_worker
        self._parser = ConversationParser()
        self._archive_builder = ArchiveBuilder()

    def export_conversation(
        self,
        context: TaskContext,
        conversation_item: ConversationListItem,
        settings: ApplicationSettings,
        destination_root: Path,
    ) -> dict[str, Any]:
        """Export one selected conversation in a managed worker task."""
        context.check_cancelled()
        context.report_progress("Opening conversation", 2.0, conversation_item.title, force=True)
        self._wait(self._browser_worker.submit("open_conversation", url=conversation_item.url))
        context.check_cancelled()

        def browser_progress(stage: str, percentage: float, item: str, completed: int, total: int) -> None:
            scaled = 3.0 + (percentage / 100.0) * 17.0
            context.report_progress(stage, scaled, item, completed, total)

        loaded = self._wait(
            self._browser_worker.submit(
                "load_complete_conversation",
                performance=settings.performance,
                cancellation_event=context.cancellation_event,
                progress_callback=browser_progress,
            )
        )
        context.check_cancelled()
        context.report_progress("Parsing conversation", 20.0, loaded["title"], force=True)
        conversation = self._parser.parse(
            html=loaded["html"],
            url=loaded["url"],
            title=loaded["title"] or conversation_item.title,
            exported_at=datetime.now(UTC),
        )
        if not conversation.messages:
            raise RuntimeError("No conversation messages were found after loading completed.")

        def resource_loader(source_url: str) -> dict[str, Any]:
            context.check_cancelled()
            return self._wait(self._browser_worker.submit("download_resource", source_url=source_url))

        def archive_progress(stage: str, percentage: float, item: str, completed: int, total: int) -> None:
            context.report_progress(stage, percentage, item, completed, total)

        result = self._archive_builder.build(
            conversation=conversation,
            settings=settings,
            destination_root=destination_root,
            resource_loader=resource_loader,
            cancellation_event=context.cancellation_event,
            progress_reporter=archive_progress,
        )
        context.emit(EventType.NOTIFICATION, {"level": "success", "message": f"Export completed: {conversation.title}"})
        return result

    @staticmethod
    def _wait(future: concurrent.futures.Future[Any], timeout: float = 900.0) -> Any:
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise TimeoutError("Browser operation exceeded the allowed time.") from exc
