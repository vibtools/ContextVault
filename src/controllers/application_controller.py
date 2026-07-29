"""Application workflow orchestration and UI-safe command boundary."""

from __future__ import annotations

import concurrent.futures
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.browser.session_worker import BrowserSessionWorker
from src.core.export_pipeline import ExportPipeline
from src.core.task_manager import TaskContext, TaskManager
from src.models.conversation import ConversationListItem
from src.models.settings import ApplicationSettings
from src.models.tasks import EventType
from src.services.archive_repository import ArchiveRepository
from src.services.config_service import ConfigService
from src.services.history_service import HistoryService
from src.utils.paths import application_root

LOGGER = logging.getLogger(__name__)


class ApplicationController:
    """Coordinate UI actions without performing heavy work on the UI thread."""

    def __init__(self, config_service: ConfigService, history_service: HistoryService) -> None:
        self.config_service = config_service
        self.history_service = history_service
        self.settings = config_service.load()
        self.task_manager = TaskManager(self.settings.performance.worker_threads)
        self.browser_worker = BrowserSessionWorker(self.task_manager.executor)
        self.export_pipeline = ExportPipeline(self.browser_worker)
        self.archive_repository = ArchiveRepository()
        self.events = self.task_manager.events
        self._conversations: list[ConversationListItem] = []
        self._current_export_task: str | None = None
        self._resume_items: list[ConversationListItem] = []
        self._resume_lock = threading.Lock()
        self._settings_lock = threading.Lock()
        self._shutdown_lock = threading.Lock()
        self._is_shutdown = False

    @property
    def conversations(self) -> list[ConversationListItem]:
        """Return a copy of the current scanned conversation list."""
        return list(self._conversations)

    def launch_browser(self) -> str:
        """Launch Chrome from a managed background task."""
        return self._submit_browser_task("Launch Chrome", "launch", settings=self.get_settings().browser)

    def connect_browser(self) -> str:
        """Connect to an existing remote-debugging Chrome instance."""
        return self._submit_browser_task(
            "Connect Chrome",
            "connect_existing",
            endpoint=self.get_settings().browser.cdp_endpoint,
        )

    def close_browser(self) -> str:
        """Close the active browser session."""
        return self._submit_browser_task("Close Chrome", "close")

    def refresh_browser(self) -> str:
        """Refresh the active browser page."""
        return self._submit_browser_task("Refresh Chrome", "refresh")

    def open_conversation(self, item: ConversationListItem) -> str:
        """Open one scanned conversation in the managed Chrome session."""
        return self._submit_browser_task("Open conversation", "open_conversation", url=item.url)

    def scan_conversations(self) -> str:
        """Scan the ChatGPT sidebar in the browser worker."""
        def work(context: TaskContext) -> dict[str, Any]:
            context.report_progress("Scanning conversations", 0.0, force=True)

            def scan_progress(stage: str, percentage: float, item: str, completed: int, total: int) -> None:
                context.report_progress(stage, percentage, item, completed, total)

            items = self._wait(
                self.browser_worker.submit(
                    "scan_conversations",
                    cancellation_event=context.cancellation_event,
                    progress_callback=scan_progress,
                )
            )
            self._conversations = list(items)
            payload = {
                "items": [item.model_dump(mode="json", by_alias=True) for item in items],
                "count": len(items),
            }
            context.emit(EventType.CONVERSATIONS, payload)
            context.report_progress("Scan complete", 100.0, f"{len(items)} conversations", len(items), len(items), force=True)
            return payload

        return self.task_manager.submit("Scan conversations", work)

    def export_conversations(self, items: list[ConversationListItem]) -> str:
        """Export selected conversations sequentially to preserve browser ownership."""
        if not items:
            raise ValueError("Select at least one conversation to export.")
        selected = list(items)
        destination = self._resolved_export_root()
        settings_snapshot = self.get_settings()

        def work(context: TaskContext) -> dict[str, Any]:
            results: list[dict[str, Any]] = []
            remaining = list(selected)
            try:
                for index, item in enumerate(selected, start=1):
                    context.check_cancelled()
                    context.report_progress(
                        "Export queue",
                        ((index - 1) / len(selected)) * 100.0,
                        item.title,
                        index - 1,
                        len(selected),
                        force=True,
                    )
                    result = self.export_pipeline.export_conversation(
                        context,
                        item,
                        settings_snapshot,
                        destination,
                    )
                    results.append(result)
                    remaining.pop(0)
                    self.history_service.append(
                        {
                            "exportedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                            "conversationId": result["conversationId"],
                            "title": result["title"],
                            "archivePath": result["archivePath"],
                            "zipPath": result["zipPath"],
                            "messageCount": result["messageCount"],
                            "status": "completed",
                        }
                    )
            except Exception:
                with self._resume_lock:
                    self._resume_items = remaining
                raise
            with self._resume_lock:
                self._resume_items = []
            context.emit(EventType.ARCHIVES, {"items": self.list_archives()})
            context.emit(EventType.HISTORY, {"items": self.history_service.list_records()})
            return {"exports": results, "count": len(results)}

        task_id = self.task_manager.submit("Export conversations", work)
        self._current_export_task = task_id
        return task_id

    def cancel_export(self) -> bool:
        """Request cancellation while preserving the current-session queue for resume."""
        return bool(self._current_export_task and self.task_manager.cancel(self._current_export_task))

    def resume_export(self) -> str:
        """Restart remaining current-session conversations after cancellation/failure."""
        with self._resume_lock:
            items = list(self._resume_items)
        if not items:
            raise RuntimeError("No interrupted export session is available to resume.")
        return self.export_conversations(items)

    def get_settings(self) -> ApplicationSettings:
        """Return a validated settings snapshot."""
        with self._settings_lock:
            return ApplicationSettings.model_validate(self.settings.model_dump())

    def save_settings(self, settings: ApplicationSettings) -> str:
        """Validate and persist UI settings outside the UI thread."""
        validated = ApplicationSettings.model_validate(settings.model_dump())

        def work(context: TaskContext) -> dict[str, Any]:
            self.config_service.save(validated)
            with self._settings_lock:
                self.settings = validated
            context.emit(
                EventType.NOTIFICATION,
                {"level": "success", "message": "Settings saved. Worker count changes apply after restart."},
            )
            return {"saved": True}

        return self.task_manager.submit("Save settings", work)

    def list_archives(self) -> list[dict[str, Any]]:
        """Return archives under the configured destination."""
        return self.archive_repository.list_archives(self._resolved_export_root())

    def refresh_archives(self) -> str:
        """Scan archives off the UI thread."""
        def work(context: TaskContext) -> dict[str, Any]:
            items = self.list_archives()
            context.emit(EventType.ARCHIVES, {"items": items})
            return {"items": items}

        return self.task_manager.submit("Refresh archives", work)

    def validate_archive(self, archive_path: Path) -> str:
        """Validate an archive off the UI thread."""
        def work(context: TaskContext) -> dict[str, Any]:
            context.report_progress("Validating archive", 10.0, archive_path.name, force=True)
            result = self.archive_repository.validate(archive_path)
            is_valid = bool(result.get("isValid"))
            error_count = len(result.get("errors", []))
            context.report_progress("Validation complete", 100.0, archive_path.name, force=True)
            context.emit(
                EventType.NOTIFICATION,
                {
                    "level": "success" if is_valid else "error",
                    "message": (
                        "Archive validation passed."
                        if is_valid
                        else f"Archive validation failed with {error_count} error(s)."
                    ),
                },
            )
            return result

        return self.task_manager.submit("Validate archive", work)

    def delete_archive(self, archive_path: Path) -> str:
        """Delete a selected archive through a managed task."""
        def work(context: TaskContext) -> dict[str, Any]:
            self.archive_repository.delete_archive(archive_path, self._resolved_export_root())
            items = self.list_archives()
            context.emit(EventType.ARCHIVES, {"items": items})
            context.emit(EventType.NOTIFICATION, {"level": "success", "message": "Archive deleted."})
            return {"deleted": str(archive_path)}

        return self.task_manager.submit("Delete archive", work)

    def rebuild_summary(self, archive_path: Path) -> str:
        """Rebuild a selected archive summary through a managed task."""
        def work(context: TaskContext) -> dict[str, Any]:
            context.report_progress("Rebuilding summary", 20.0, archive_path.name, force=True)
            result = self.archive_repository.rebuild_summary(archive_path)
            context.report_progress("Summary rebuilt", 100.0, archive_path.name, force=True)
            context.emit(EventType.NOTIFICATION, {"level": "success", "message": "Summary rebuilt."})
            return result

        return self.task_manager.submit("Rebuild summary", work)

    def open_archive(self, archive_path: Path) -> bool:
        """Open a selected archive Markdown file."""
        return self.archive_repository.open_archive(archive_path)

    def open_archive_folder(self, archive_path: Path) -> bool:
        """Open a selected archive folder."""
        return self.archive_repository.open_folder(archive_path)

    def refresh_history(self) -> str:
        """Load export history outside the UI thread."""
        def work(context: TaskContext) -> dict[str, Any]:
            items = self.history_service.list_records()
            context.emit(EventType.HISTORY, {"items": items})
            return {"items": items}

        return self.task_manager.submit("Refresh history", work)

    def browser_status(self) -> str:
        """Request a browser status update."""
        return self._submit_browser_task("Browser status", "status")

    def shutdown(self) -> None:
        """Cancel work, close browser resources, and stop the executor safely."""
        with self._shutdown_lock:
            if self._is_shutdown:
                return
            self._is_shutdown = True
        self.task_manager.cancel_all()
        try:
            self.browser_worker.stop()
        finally:
            self.task_manager.shutdown()

    def _submit_browser_task(self, task_name: str, command: str, **kwargs: Any) -> str:
        def work(context: TaskContext) -> dict[str, Any]:
            context.report_progress(task_name, 10.0, force=True)
            result = self._wait(self.browser_worker.submit(command, **kwargs))
            context.emit(EventType.BROWSER, result)
            context.report_progress(task_name, 100.0, force=True)
            return result

        return self.task_manager.submit(task_name, work)

    def _resolved_export_root(self) -> Path:
        configured = Path(self.get_settings().export.default_folder).expanduser()
        if not configured.is_absolute():
            configured = application_root() / configured
        return configured.resolve()

    @staticmethod
    def _wait(future: concurrent.futures.Future[Any], timeout: float = 900.0) -> Any:
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise TimeoutError("Background browser operation timed out.") from exc
