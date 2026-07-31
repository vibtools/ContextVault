from __future__ import annotations

import asyncio
import concurrent.futures
import queue
import tempfile
import threading
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.browser.browser_manager import BrowserManager, _ReadinessPolicy
from src.core.archive_builder import ArchiveBuilder
from src.core.archive_validator import ArchiveValidator
from src.core.export_pipeline import ExportPipeline
from src.core.message_checkpoint import MessageCheckpointStore
from src.core.task_manager import TaskContext
from src.models.conversation import CodeReference, ConversationListItem, ConversationMessage
from src.models.settings import ApplicationSettings, PerformanceSettings
from src.parsers.conversation_parser import ConversationParser
from src.utils.json_io import read_json
from src.utils.text import estimated_tokens, word_count


class _HeadLocator:
    async def inner_html(self) -> str:
        return "<meta charset='utf-8'>"


class _ReloadablePage:
    def __init__(self, states: list[dict[str, object]]) -> None:
        self.states = states
        self.index = 0
        self.reload_count = 0
        self.url = "https://chatgpt.com/c/incremental"

    async def evaluate(self, script: str, _payload: object | None = None) -> object:
        if "delete window.__contextVaultObservationV2" in script:
            return None
        value = self.states[min(self.index, len(self.states) - 1)]
        self.index += 1
        return dict(value)

    async def reload(self, *, wait_until: str) -> None:
        self.reload_count += 1
        self.index = min(self.index, len(self.states) - 3)

    def locator(self, selector: str) -> _HeadLocator:
        if selector != "head":
            raise AssertionError(selector)
        return _HeadLocator()


def _message_item(key: str = "message-1") -> dict[str, object]:
    return {
        "key": key,
        "signature": "assistant:stable",
        "role": "assistant",
        "fallback": False,
        "domIndex": 0,
        "documentTop": 0,
        "html": (
            f'<article data-message-id="{key}" data-message-author-role="assistant">'
            '<div class="markdown"><pre><code class="language-python">print("ok")\n</code></pre></div>'
            "</article>"
        ),
        "text": 'print("ok")',
        "timestamp": "2026-07-29T12:00:00Z",
        "capturedAt": "2026-07-29T12:01:00Z",
        "imageCount": 0,
        "pendingImages": 0,
        "attachmentCount": 0,
        "codeBlockCount": 1,
        "tableCount": 0,
    }


def _ready_state(item: dict[str, object]) -> dict[str, object]:
    return {
        "documentReady": True,
        "appReady": True,
        "conversationContainer": True,
        "messageCount": 1,
        "messages": [item],
        "mutationRevision": 0,
        "mutationIdleMs": 1000,
        "beforeScrollTop": 0,
        "afterScrollTop": 0,
        "scrollHeight": 1000,
        "clientHeight": 800,
        "atTop": True,
        "streaming": False,
        "continueRequired": False,
        "loadingCount": 0,
        "imageCount": 0,
        "pendingImages": 0,
        "attachmentCount": 0,
        "codeBlockCount": 1,
        "tableCount": 0,
        "title": "Incremental",
        "model": "GPT",
        "workspace": "Personal",
        "accessDenied": False,
        "fallbackMessageKeys": 0,
        "windowReadyToScroll": True,
        "url": "https://chatgpt.com/c/incremental",
    }


class _PipelineWorker:
    def __init__(self, item: dict[str, object]) -> None:
        self.item = item

    def submit(self, command: str, **kwargs: object) -> concurrent.futures.Future[object]:
        future: concurrent.futures.Future[object] = concurrent.futures.Future()
        if command == "open_conversation":
            future.set_result({"url": kwargs["url"], "title": "Incremental"})
        elif command == "load_complete_conversation":
            callback = kwargs["message_checkpoint_callback"]
            result = callback([self.item], (str(self.item["key"]),), set())
            if result["failed"]:
                future.set_exception(RuntimeError(result["failed"]))
            else:
                future.set_result(
                    {
                        "html": "<html></html>",
                        "url": "https://chatgpt.com/c/incremental",
                        "title": "Incremental",
                        "messageCount": 1,
                        "messageKeys": [self.item["key"]],
                        "assetCounts": {"images": 0, "attachments": 0, "codeBlocks": 1, "tables": 0},
                        "browserName": "Google Chrome",
                        "browserVersion": "138.0",
                        "browserProfile": "Default",
                        "chatgptModel": "GPT",
                        "chatgptWorkspace": "Personal",
                        "estimatedSize": 256,
                        "readiness": {
                            "incrementalVerification": True,
                            "checkpointedMessages": 1,
                            "checkpointReloads": 0,
                            "messageRetryCount": 5,
                        },
                    }
                )
        else:
            future.set_exception(AssertionError(command))
        return future


class IncrementalCheckpointTests(unittest.TestCase):
    def test_code_validation_preserves_crlf_bytes(self) -> None:
        html = Path("tests/fixtures/sample_conversation.html").read_text(encoding="utf-8")
        conversation = ConversationParser().parse(
            html=html,
            url="https://chatgpt.com/c/crlf",
            title="CRLF",
            exported_at=datetime(2026, 7, 29, tzinfo=UTC),
        )
        code = conversation.messages[1].code_references[0]
        code.raw_code = "line1\r\nline2\r\n"
        code.character_count = len(code.raw_code)
        code.line_count = len(code.raw_code.splitlines())
        settings = ApplicationSettings.model_validate(
            {
                "assets": {"images": False, "attachments": False, "tables": False},
                "export": {"archiveName": "crlf", "verifyExport": True},
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            result = ArchiveBuilder().build(
                conversation=conversation,
                settings=settings,
                destination_root=Path(directory),
                resource_loader=lambda _url: {},
                cancellation_event=threading.Event(),
            )
            archive = Path(result["archivePath"])
            code_path = next((archive / "assets/code").iterdir())
            self.assertEqual(code_path.read_bytes(), b"line1\r\nline2\r\n")
            self.assertTrue(ArchiveValidator().validate(archive).is_valid)

    def test_unix_message_timestamp_is_preserved_as_real_source_time(self) -> None:
        parser = ConversationParser()
        message = parser.parse_message_fragment(
            html=(
                '<article data-message-id="unix" data-message-author-role="assistant" '
                'data-message-timestamp="1785326400000"><div class="markdown">Timed</div></article>'
            ),
            sequence_number=1,
            conversation_id="unix",
            base_url="https://chatgpt.com/c/unix",
            captured_at=datetime(2026, 7, 29, 12, 1, tzinfo=UTC),
        )
        self.assertEqual(message.timestamp, datetime(2026, 7, 29, 12, 0, tzinfo=UTC))
        self.assertEqual(message.timestamp_source, "message_timestamp")

    def test_partial_middle_timestamp_does_not_invent_conversation_boundaries(self) -> None:
        parser = ConversationParser()
        messages = [
            ConversationMessage(
                messageId="first",
                sequenceNumber=1,
                role="user",
                plainText="First",
                markdown="First",
                characterCount=5,
                wordCount=1,
                estimatedTokens=2,
            ),
            ConversationMessage(
                messageId="middle",
                sequenceNumber=2,
                role="assistant",
                plainText="Middle",
                markdown="Middle",
                timestamp="2026-07-20T12:00:00Z",
                timestampSource="message_timestamp",
                characterCount=6,
                wordCount=1,
                estimatedTokens=2,
            ),
            ConversationMessage(
                messageId="last",
                sequenceNumber=3,
                role="user",
                plainText="Last",
                markdown="Last",
                characterCount=4,
                wordCount=1,
                estimatedTokens=1,
            ),
        ]
        conversation = parser.build_record(
            messages=messages,
            url="https://chatgpt.com/c/partial-time",
            title="Partial Time",
            exported_at=datetime(2026, 7, 29, tzinfo=UTC),
        )
        self.assertIsNone(conversation.created_at)
        self.assertIsNone(conversation.updated_at)
        self.assertIsNone(conversation.duration_seconds)
        self.assertEqual(conversation.timestamp_source, "unknown")

    def test_large_conversation_with_mixed_line_endings_validates(self) -> None:
        parser = ConversationParser()
        messages: list[ConversationMessage] = []
        for index in range(1, 273):
            raw_code = ""
            references: list[CodeReference] = []
            if index % 3 == 0:
                raw_code = f"step_{index} = True\r\nprint(step_{index})\r\n"
                references.append(
                    CodeReference(
                        id=f"message-{index}-code-001",
                        language="python",
                        rawCode=raw_code,
                        characterCount=len(raw_code),
                        lineCount=len(raw_code.splitlines()),
                    )
                )
            text = f"Message {index}"
            messages.append(
                ConversationMessage(
                    messageId=f"message-{index}",
                    sequenceNumber=index,
                    role="assistant" if index % 2 == 0 else "user",
                    plainText=text,
                    markdown=text,
                    html=f"<p>{text}</p>",
                    codeReferences=references,
                    capturedAt="2026-07-29T12:01:00Z",
                    sourceKey=f"message-{index}",
                    sourceSignature=f"signature-{index}",
                    characterCount=len(text),
                    wordCount=word_count(text),
                    estimatedTokens=estimated_tokens(text),
                )
            )
        conversation = parser.build_record(
            messages=messages,
            url="https://chatgpt.com/c/large-crlf",
            title="Large CRLF",
            exported_at=datetime(2026, 7, 29, tzinfo=UTC),
        )
        settings = ApplicationSettings.model_validate(
            {
                "assets": {"images": False, "attachments": False, "tables": False},
                "export": {"archiveName": "large-crlf", "verifyExport": True},
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            result = ArchiveBuilder().build(
                conversation=conversation,
                settings=settings,
                destination_root=Path(directory),
                resource_loader=lambda _url: {},
                cancellation_event=threading.Event(),
            )
            validation = ArchiveValidator().validate(Path(result["archivePath"]))
            self.assertTrue(validation.is_valid, validation.errors)
            self.assertEqual(result["messageCount"], 272)
            self.assertEqual(len(list((Path(result["archivePath"]) / "assets/code").iterdir())), 90)

    def test_invalid_message_is_degraded_only_after_explicit_exhaustion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MessageCheckpointStore(
                Path(directory) / "checkpoint",
                conversation_id="conversation",
                base_url="https://chatgpt.com/c/conversation",
            )
            item = {
                "key": "broken",
                "signature": "broken-signature",
                "role": "assistant",
                "html": "<div>unsupported fragment</div>",
                "text": "Recoverable visible text",
                "capturedAt": "2026-07-29T12:01:00Z",
            }
            first = store.capture_window([item], ("broken",), set())
            self.assertIn("broken", first["failed"])
            second = store.capture_window([item], ("broken",), {"broken"})
            self.assertEqual(second["skippedKeys"], ["broken"])
            message = store.ordered_messages(("broken",))[0]
            self.assertEqual(message.capture_status, "skipped")
            self.assertIn("Recoverable visible text", message.plain_text)
            self.assertIsNotNone(message.captured_at)
            store.close()


    def test_repeated_degraded_checkpoint_remains_classified_as_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MessageCheckpointStore(
                Path(directory) / "checkpoint",
                conversation_id="conversation",
                base_url="https://chatgpt.com/c/conversation",
            )
            item = {
                "key": "broken",
                "signature": "broken-signature",
                "role": "assistant",
                "html": "<div>unsupported fragment</div>",
                "text": "Recoverable visible text",
                "capturedAt": "2026-07-29T12:01:00Z",
            }
            store.capture_window([item], ("broken",), {"broken"})
            repeated = store.capture_window([item], ("broken",), set())
            self.assertEqual(repeated["verifiedKeys"], [])
            self.assertEqual(repeated["skippedKeys"], ["broken"])
            store.close()

    def test_degraded_message_archive_publishes_with_warning(self) -> None:
        parser = ConversationParser()
        verified_text = "Verified context"
        degraded_text = "Visible fallback context"
        messages = [
            ConversationMessage(
                messageId="verified",
                sequenceNumber=1,
                role="user",
                plainText=verified_text,
                markdown=verified_text,
                html=f"<p>{verified_text}</p>",
                capturedAt="2026-07-29T12:00:00Z",
                sourceKey="verified",
                sourceSignature="verified-signature",
                characterCount=len(verified_text),
                wordCount=word_count(verified_text),
                estimatedTokens=estimated_tokens(verified_text),
            ),
            ConversationMessage(
                messageId="degraded",
                sequenceNumber=2,
                role="assistant",
                plainText=degraded_text,
                markdown=degraded_text,
                html="",
                capturedAt="2026-07-29T12:01:00Z",
                captureStatus="skipped",
                captureAttempts=6,
                captureError="persistent mismatch",
                sourceKey="degraded",
                sourceSignature="degraded-signature",
                characterCount=len(degraded_text),
                wordCount=word_count(degraded_text),
                estimatedTokens=estimated_tokens(degraded_text),
            ),
        ]
        conversation = parser.build_record(
            messages=messages,
            url="https://chatgpt.com/c/degraded",
            title="Degraded",
            exported_at=datetime(2026, 7, 29, tzinfo=UTC),
            capture_warnings=["Message degraded was preserved after retries."],
            readiness={"incrementalVerification": True},
        )
        settings = ApplicationSettings.model_validate(
            {
                "assets": {"images": False, "attachments": False, "tables": False},
                "performance": {"messageRetryCount": 5},
                "export": {"archiveName": "degraded", "verifyExport": True},
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            result = ArchiveBuilder().build(
                conversation=conversation,
                settings=settings,
                destination_root=Path(directory),
                resource_loader=lambda _url: {},
                cancellation_event=threading.Event(),
            )
            archive = Path(result["archivePath"])
            validation = ArchiveValidator().validate(archive)
            self.assertTrue(validation.is_valid, validation.errors)
            self.assertTrue(any("degraded content" in warning for warning in validation.warnings))
            manifest = read_json(archive / "manifest.json")
            self.assertEqual(manifest["data"]["skippedMessages"], 1)
            self.assertEqual(manifest["data"]["verifiedMessages"], 1)
            self.assertIn("WARNING: Message degraded", (archive / "logs/export.log").read_text(encoding="utf-8"))

    def test_pipeline_generates_timestamped_manifest_from_incremental_messages(self) -> None:
        item = _message_item()
        worker = _PipelineWorker(item)
        pipeline = ExportPipeline(worker)  # type: ignore[arg-type]
        context = TaskContext("incremental", threading.Event(), queue.Queue())
        conversation_item = ConversationListItem(
            conversationId="incremental",
            title="Incremental",
            url="https://chatgpt.com/c/incremental",
        )
        settings = ApplicationSettings.model_validate(
            {
                "assets": {"images": False, "attachments": False, "tables": False},
                "performance": {"messageRetryCount": 5},
                "export": {"archiveName": "incremental", "verifyExport": True},
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            checkpoint_data = Path(directory) / "data"
            with patch("src.core.export_pipeline.data_directory", return_value=checkpoint_data):
                result = pipeline.export_conversation(
                    context,
                    conversation_item,
                    settings,
                    Path(directory) / "exports",
                )
            archive = Path(result["archivePath"])
            manifest = read_json(archive / "manifest.json")
            metadata = read_json(archive / "metadata.json")
            conversation = read_json(archive / "conversation.json")
            self.assertTrue(manifest["data"]["incrementalVerification"])
            self.assertEqual(manifest["data"]["messageRetryCount"], 5)
            self.assertEqual(manifest["data"]["conversationStartedAt"], "2026-07-29T12:00:00Z")
            self.assertEqual(manifest["data"]["conversationEndedAt"], "2026-07-29T12:00:00Z")
            self.assertIsNotNone(manifest["data"]["exportedAt"])
            self.assertEqual(metadata["data"]["timestampSource"], "message_timestamp")
            self.assertEqual(conversation["data"]["messages"][0]["capturedAt"], "2026-07-29T12:01:00Z")
            for relative in (
                "manifest.json",
                "metadata.json",
                "conversation.json",
                "summary.json",
                "search-index.json",
                "statistics.json",
                "rag/chunks.json",
                "rag/documents.json",
                "rag/keywords.json",
                "rag/chunk-map.json",
            ):
                self.assertIsNotNone(read_json(archive / relative)["generatedAt"])
            self.assertIn("Conversation documents generated", (archive / "logs/export.log").read_text(encoding="utf-8"))
            self.assertFalse(any((checkpoint_data / "checkpoints").glob("*")))


class BrowserCheckpointRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_checkpoint_reloads_then_resumes(self) -> None:
        item = _message_item()
        state = _ready_state(item)
        page = _ReloadablePage([state, state, state, state, state, state, state, state])
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]
        calls = 0

        def checkpoint(items: list[dict[str, object]], order: tuple[str, ...], skip: set[str]) -> dict[str, object]:
            nonlocal calls
            calls += 1
            key = str(items[0]["key"])
            if calls == 1:
                return {"verifiedKeys": [], "skippedKeys": [], "failed": {key: "temporary mismatch"}}
            return {"verifiedKeys": [key], "skippedKeys": [], "failed": {}}

        policy = _ReadinessPolicy(
            timeout_seconds=0.5,
            stability_window_seconds=0.0,
            minimum_stable_observations=1,
            initial_poll_seconds=0.001,
            maximum_poll_seconds=0.002,
        )
        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=policy),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="138.0")),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(messageRetryCount=1),
                cancellation_event=threading.Event(),
                message_checkpoint_callback=checkpoint,  # type: ignore[arg-type]
            )
        self.assertEqual(page.reload_count, 1)
        self.assertEqual(loaded["readiness"]["checkpointReloads"], 1)
        self.assertEqual(loaded["readiness"]["checkpointedMessages"], 1)

    async def test_exhausted_checkpoint_is_skipped_after_reload_without_failing_export(self) -> None:
        item = _message_item("message-exhausted")
        state = _ready_state(item)
        page = _ReloadablePage([state, state, state, state, state, state, state, state, state, state])
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]
        skipped: list[str] = []

        def checkpoint(items: list[dict[str, object]], order: tuple[str, ...], skip: set[str]) -> dict[str, object]:
            key = str(items[0]["key"])
            if key in skip:
                skipped.append(key)
                return {"verifiedKeys": [], "skippedKeys": [key], "failed": {}}
            return {"verifiedKeys": [], "skippedKeys": [], "failed": {key: "persistent mismatch"}}

        policy = _ReadinessPolicy(
            timeout_seconds=0.5,
            stability_window_seconds=0.0,
            minimum_stable_observations=1,
            initial_poll_seconds=0.001,
            maximum_poll_seconds=0.002,
        )
        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=policy),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="138.0")),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(messageRetryCount=1),
                cancellation_event=threading.Event(),
                message_checkpoint_callback=checkpoint,  # type: ignore[arg-type]
            )
        self.assertEqual(page.reload_count, 1)
        self.assertEqual(skipped, ["message-exhausted"])
        self.assertEqual(loaded["messageCount"], 1)
        self.assertEqual(loaded["readiness"]["checkpointedMessages"], 1)


if __name__ == "__main__":
    unittest.main()
