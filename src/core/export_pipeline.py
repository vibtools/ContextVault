"""End-to-end browser extraction and archive export workflow."""

from __future__ import annotations

import concurrent.futures
import logging
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from src.browser.session_worker import BrowserSessionWorker
from src.core.archive_builder import ArchiveBuilder
from src.core.task_manager import TaskContext
from src.models.conversation import ConversationListItem, ConversationRecord
from src.models.settings import ApplicationSettings, PerformanceSettings
from src.models.tasks import EventType
from src.parsers.conversation_parser import ConversationParser

LOGGER = logging.getLogger(__name__)


class _ExportState(StrEnum):
    INITIALIZING = "INITIALIZING"
    CONNECT_BROWSER = "CONNECT_BROWSER"
    OPEN_CONVERSATION = "OPEN_CONVERSATION"
    WAIT_BROWSER_READY = "WAIT_BROWSER_READY"
    WAIT_DOM_READY = "WAIT_DOM_READY"
    WAIT_REACT_READY = "WAIT_REACT_READY"
    WAIT_CONVERSATION_READY = "WAIT_CONVERSATION_READY"
    WAIT_MESSAGE_STABILIZATION = "WAIT_MESSAGE_STABILIZATION"
    DEEP_SCAN = "DEEP_SCAN"
    COLLECT_METADATA = "COLLECT_METADATA"
    COLLECT_MESSAGES = "COLLECT_MESSAGES"
    COLLECT_IMAGES = "COLLECT_IMAGES"
    COLLECT_ATTACHMENTS = "COLLECT_ATTACHMENTS"
    COLLECT_CODE_BLOCKS = "COLLECT_CODE_BLOCKS"
    VALIDATE_EXPORT = "VALIDATE_EXPORT"
    GENERATE_JSON = "GENERATE_JSON"
    VERIFY_ARCHIVE = "VERIFY_ARCHIVE"
    SAVE_ARCHIVE = "SAVE_ARCHIVE"
    EXPORT_COMPLETE = "EXPORT_COMPLETE"


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
        self._transition(context, _ExportState.INITIALIZING, 0.0, conversation_item.title)
        context.check_cancelled()

        self._transition(context, _ExportState.CONNECT_BROWSER, 1.0, conversation_item.title)
        status = self._wait(self._browser_worker.submit("status"), timeout=30.0)
        if not bool(status.get("connected")):
            raise RuntimeError("Google Chrome is not connected. Launch or connect Chrome before exporting.")

        self._transition(context, _ExportState.OPEN_CONVERSATION, 3.0, conversation_item.title)
        self._wait(
            self._browser_worker.submit("open_conversation", url=conversation_item.url),
            timeout=120.0,
        )
        context.check_cancelled()
        self._transition(context, _ExportState.WAIT_BROWSER_READY, 5.0, conversation_item.title)

        last_readiness_state: _ExportState | None = None

        def browser_progress(stage: str, percentage: float, item: str, completed: int, total: int) -> None:
            nonlocal last_readiness_state
            mapped_state = _state_for_browser_stage(stage)
            if mapped_state is not None and mapped_state != last_readiness_state:
                LOGGER.info("Export state transition: %s", mapped_state.value)
                last_readiness_state = mapped_state
            scaled = 5.0 + (percentage / 100.0) * 40.0
            context.report_progress(stage, scaled, item, completed, total)

        loaded = self._wait(
            self._browser_worker.submit(
                "load_complete_conversation",
                performance=settings.performance,
                cancellation_event=context.cancellation_event,
                progress_callback=browser_progress,
            ),
            timeout=_browser_operation_timeout(settings.performance),
        )
        context.check_cancelled()
        self._validate_loaded_payload(loaded, conversation_item)
        resolved_title = _resolved_conversation_title(loaded.get("title"), conversation_item.title)
        loaded["title"] = resolved_title
        for state, percentage in (
            (_ExportState.WAIT_DOM_READY, 42.0),
            (_ExportState.WAIT_REACT_READY, 43.0),
            (_ExportState.WAIT_CONVERSATION_READY, 44.0),
            (_ExportState.WAIT_MESSAGE_STABILIZATION, 45.0),
        ):
            self._transition(context, state, percentage, loaded["title"])

        self._transition(context, _ExportState.DEEP_SCAN, 48.0, loaded["title"])
        exported_at_utc = datetime.now(UTC)
        exported_at_local = datetime.now().astimezone()
        conversation = self._parser.parse(
            html=loaded["html"],
            url=loaded["url"],
            title=resolved_title,
            exported_at=exported_at_utc,
            exported_at_local=exported_at_local,
            export_id=str(uuid4()),
            browser_name=str(loaded.get("browserName") or "unavailable"),
            browser_version=str(loaded.get("browserVersion") or "unavailable"),
            browser_profile=str(loaded.get("browserProfile") or "unavailable"),
            chatgpt_workspace=_optional_text(loaded.get("chatgptWorkspace")),
            chatgpt_model=_optional_text(loaded.get("chatgptModel")),
            estimated_size=int(loaded.get("estimatedSize") or 0),
            source_message_count=int(loaded.get("messageCount") or 0),
            source_asset_counts=_integer_mapping(loaded.get("assetCounts")),
            readiness=dict(loaded.get("readiness") or {}),
        )

        self._transition(context, _ExportState.COLLECT_METADATA, 52.0, conversation.title)
        self._transition(context, _ExportState.COLLECT_MESSAGES, 56.0, f"{len(conversation.messages)} messages")
        self._validate_conversation(conversation)
        self._transition(context, _ExportState.VALIDATE_EXPORT, 60.0, "Pre-export validation passed")

        def resource_loader(source_url: str) -> dict[str, Any]:
            context.check_cancelled()
            return self._wait(
                self._browser_worker.submit("download_resource", source_url=source_url),
                timeout=360.0,
            )

        last_archive_state: _ExportState | None = None

        def archive_progress(stage: str, percentage: float, item: str, completed: int, total: int) -> None:
            nonlocal last_archive_state
            mapped_state = _state_for_archive_stage(stage)
            if mapped_state is not None and mapped_state != last_archive_state:
                LOGGER.info("Export state transition: %s", mapped_state.value)
                last_archive_state = mapped_state
            scaled = 60.0 + (percentage / 100.0) * 38.0
            context.report_progress(stage, scaled, item, completed, total)

        self._transition(context, _ExportState.COLLECT_IMAGES, 61.0, conversation.title)
        self._transition(context, _ExportState.COLLECT_ATTACHMENTS, 62.0, conversation.title)
        self._transition(context, _ExportState.COLLECT_CODE_BLOCKS, 63.0, conversation.title)
        self._transition(context, _ExportState.GENERATE_JSON, 64.0, conversation.title)
        result = self._archive_builder.build(
            conversation=conversation,
            settings=settings,
            destination_root=destination_root,
            resource_loader=resource_loader,
            cancellation_event=context.cancellation_event,
            progress_reporter=archive_progress,
        )
        self._transition(context, _ExportState.VERIFY_ARCHIVE, 98.0, conversation.title)
        validation = result.get("validation") or {}
        if not bool(validation.get("isValid")):
            raise RuntimeError("Archive verification did not return a valid result.")
        self._transition(context, _ExportState.SAVE_ARCHIVE, 99.0, result["archivePath"])
        self._transition(context, _ExportState.EXPORT_COMPLETE, 100.0, conversation.title)
        context.emit(
            EventType.NOTIFICATION,
            {"level": "success", "message": f"Export completed: {conversation.title}"},
        )
        return result

    @staticmethod
    def _validate_loaded_payload(loaded: dict[str, Any], item: ConversationListItem) -> None:
        required_text = {
            "html": loaded.get("html"),
            "url": loaded.get("url"),
            "title": loaded.get("title") or item.title,
            "browserName": loaded.get("browserName"),
            "browserVersion": loaded.get("browserVersion"),
            "browserProfile": loaded.get("browserProfile"),
        }
        missing = [name for name, value in required_text.items() if not str(value or "").strip()]
        if missing:
            raise RuntimeError(f"Conversation readiness metadata is incomplete: {', '.join(missing)}")
        if str(loaded.get("browserVersion")).strip().lower() == "unavailable":
            raise RuntimeError("Google Chrome version could not be detected; export metadata would be incomplete.")
        message_count = int(loaded.get("messageCount") or 0)
        if message_count <= 0:
            raise RuntimeError(
                "Conversation readiness completed without any accumulated messages; no partial export was written."
            )
        parsed_url = urlparse(str(loaded["url"]))
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise RuntimeError("Conversation readiness returned an invalid source URL.")
        readiness = loaded.get("readiness")
        if not isinstance(readiness, dict):
            raise RuntimeError("Conversation readiness verification report is missing.")
        required_flags = (
            "documentReady",
            "reactReady",
            "conversationContainer",
            "streamingComplete",
            "lazyLoadingComplete",
            "imagesReady",
        )
        failed_flags = [name for name in required_flags if readiness.get(name) is not True]
        if failed_flags:
            raise RuntimeError(
                "Conversation readiness verification failed: " + ", ".join(sorted(failed_flags))
            )
        if int(readiness.get("messageCount") or 0) != message_count:
            raise RuntimeError("Conversation readiness message count is internally inconsistent.")

    @staticmethod
    def _validate_conversation(conversation: ConversationRecord) -> None:
        errors: list[str] = []
        if not conversation.conversation_id.strip():
            errors.append("conversation ID is missing")
        if not conversation.title.strip():
            errors.append("conversation title is missing")
        if not conversation.url.startswith(("https://", "http://")):
            errors.append("conversation URL is invalid")
        if not conversation.export_id.strip():
            errors.append("export UUID is missing")
        if conversation.exported_at.tzinfo is None:
            errors.append("UTC export timestamp is not timezone-aware")
        if conversation.exported_at_local is None or conversation.exported_at_local.tzinfo is None:
            errors.append("local export timestamp is missing or not timezone-aware")
        if conversation.browser_name == "unavailable":
            errors.append("browser name is unavailable")
        if conversation.browser_version == "unavailable":
            errors.append("browser version is unavailable")
        if conversation.browser_profile == "unavailable":
            errors.append("browser profile is unavailable")
        if conversation.estimated_size <= 0:
            errors.append("estimated source size is unavailable")
        if not conversation.messages:
            errors.append("conversation contains no messages")

        identifiers: set[str] = set()
        for index, message in enumerate(conversation.messages, start=1):
            if message.sequence_number != index:
                errors.append(f"message {message.message_id} sequence is not contiguous")
            if not message.message_id.strip():
                errors.append(f"message {index} has no identifier")
            elif message.message_id in identifiers:
                errors.append(f"duplicate message identifier: {message.message_id}")
            identifiers.add(message.message_id)
            has_content = bool(
                message.plain_text.strip()
                or message.markdown.strip()
                or message.html.strip()
                or message.code_references
                or message.image_references
                or message.attachment_references
                or message.table_references
                or message.citation_references
            )
            if not has_content:
                errors.append(f"message {message.message_id} has no exportable content")

        if conversation.source_message_count is not None and len(conversation.messages) != conversation.source_message_count:
            errors.append(
                "parsed message count does not match the stabilized browser snapshot "
                f"({len(conversation.messages)} != {conversation.source_message_count})"
            )
        readiness_count = int(conversation.readiness.get("messageCount") or 0)
        if readiness_count and readiness_count != len(conversation.messages):
            errors.append("readiness message count does not match parsed message count")
        if errors:
            raise RuntimeError("Pre-export validation failed: " + "; ".join(errors))
        LOGGER.info(
            "Pre-export validation passed: conversation=%s messages=%s",
            conversation.conversation_id,
            len(conversation.messages),
        )

    @staticmethod
    def _transition(
        context: TaskContext,
        state: _ExportState,
        percentage: float,
        item: str,
    ) -> None:
        LOGGER.info("Export state transition: %s", state.value)
        context.report_progress(_state_label(state), percentage, item, force=True)

    @staticmethod
    def _wait(future: concurrent.futures.Future[Any], timeout: float = 900.0) -> Any:
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise TimeoutError("Browser operation exceeded the allowed time.") from exc


def _browser_operation_timeout(performance: PerformanceSettings) -> float:
    return {"Low": 240.0, "Balanced": 1020.0, "High": 1920.0}[performance.memory_mode]


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _resolved_conversation_title(observed: Any, fallback: str) -> str:
    title = str(observed or "").strip()
    if title.casefold() in {"chatgpt", "new chat", "untitled conversation"}:
        title = ""
    fallback_title = fallback.strip()
    return title or fallback_title or "Untitled Conversation"


def _integer_mapping(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, int] = {}
    for key, item in value.items():
        try:
            output[str(key)] = max(0, int(item))
        except (TypeError, ValueError):
            continue
    return output


def _state_for_browser_stage(stage: str) -> _ExportState | None:
    normalized = stage.casefold()
    if "browser" in normalized:
        return _ExportState.WAIT_BROWSER_READY
    if "chatgpt" in normalized or "react" in normalized:
        return _ExportState.WAIT_REACT_READY
    if "detecting conversation" in normalized or "waiting for messages" in normalized:
        return _ExportState.WAIT_CONVERSATION_READY
    if any(marker in normalized for marker in ("older messages", "response", "stabil")):
        return _ExportState.WAIT_MESSAGE_STABILIZATION
    if "ready" in normalized:
        return _ExportState.DEEP_SCAN
    return None


def _state_for_archive_stage(stage: str) -> _ExportState | None:
    normalized = stage.casefold()
    if "image" in normalized:
        return _ExportState.COLLECT_IMAGES
    if "attachment" in normalized:
        return _ExportState.COLLECT_ATTACHMENTS
    if "code" in normalized:
        return _ExportState.COLLECT_CODE_BLOCKS
    if "validat" in normalized:
        return _ExportState.VERIFY_ARCHIVE
    if "archive" in normalized or "document" in normalized:
        return _ExportState.GENERATE_JSON
    return None


def _state_label(state: _ExportState) -> str:
    labels = {
        _ExportState.INITIALIZING: "Initializing export engine",
        _ExportState.CONNECT_BROWSER: "Connecting to browser",
        _ExportState.OPEN_CONVERSATION: "Opening conversation",
        _ExportState.WAIT_BROWSER_READY: "Waiting for browser",
        _ExportState.WAIT_DOM_READY: "Loading page",
        _ExportState.WAIT_REACT_READY: "Waiting for ChatGPT UI",
        _ExportState.WAIT_CONVERSATION_READY: "Detecting conversation",
        _ExportState.WAIT_MESSAGE_STABILIZATION: "Waiting for messages",
        _ExportState.DEEP_SCAN: "Deep scanning conversation",
        _ExportState.COLLECT_METADATA: "Collecting metadata",
        _ExportState.COLLECT_MESSAGES: "Collecting messages",
        _ExportState.COLLECT_IMAGES: "Collecting images",
        _ExportState.COLLECT_ATTACHMENTS: "Collecting attachments",
        _ExportState.COLLECT_CODE_BLOCKS: "Collecting code blocks",
        _ExportState.VALIDATE_EXPORT: "Validating export",
        _ExportState.GENERATE_JSON: "Generating archive",
        _ExportState.VERIFY_ARCHIVE: "Verifying archive",
        _ExportState.SAVE_ARCHIVE: "Saving archive",
        _ExportState.EXPORT_COMPLETE: "Export completed successfully",
    }
    return labels[state]
