from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from playwright.async_api import Error as PlaywrightError

from src.browser.browser_manager import (
    BrowserManager,
    _OBSERVATION_SCRIPT,
    _window_semantic_signature,
)
from src.core.message_checkpoint import (
    MessageCheckpointInfrastructureError,
    MessageCheckpointStore,
)
from src.parsers.conversation_parser import ConversationParser


class _FlakyObservationPage:
    def __init__(self) -> None:
        self.calls = 0

    async def evaluate(self, _script: str, _payload: object) -> object:
        self.calls += 1
        if self.calls == 1:
            raise PlaywrightError("transient execution context failure")
        return {"messages": [], "documentReady": True}


class ExportForensicRegressionTests(unittest.IsolatedAsyncioTestCase):
    def test_force_scroll_can_bypass_only_a_persistent_loader(self) -> None:
        self.assertIn(
            "const scrollAllowed = windowReadyToScroll || (forceScroll && baseWindowReadyToScroll);",
            _OBSERVATION_SCRIPT,
        )
        self.assertIn("if (scrollUp && scrollAllowed", _OBSERVATION_SCRIPT)
        self.assertIn("&& !streaming", _OBSERVATION_SCRIPT)
        self.assertIn("&& !continueRequired", _OBSERVATION_SCRIPT)

    def test_observer_uses_mixed_message_container_contract(self) -> None:
        self.assertIn("messageIdSelector", _OBSERVATION_SCRIPT)
        self.assertIn("selectors.join(', ')", _OBSERVATION_SCRIPT)
        self.assertIn("candidateSet.has(parent)", _OBSERVATION_SCRIPT)

    def test_nested_active_scroller_is_preferred_over_document_fallback(self) -> None:
        self.assertIn("const nestedBonus = candidate === documentScroller ? 0 : 1_000_000_000;", _OBSERVATION_SCRIPT)
        self.assertIn("const activeBonus = scrollTop > 1 ? 10_000_000_000 : 0;", _OBSERVATION_SCRIPT)
        self.assertIn("candidates.sort", _OBSERVATION_SCRIPT)

    def test_observer_semantics_include_export_critical_resource_attributes(self) -> None:
        self.assertIn("semanticSignature", _OBSERVATION_SCRIPT)
        for marker in (
            "data-download-url",
            "data-file-url",
            "data-file-id",
            "data-filename",
            "currentSrc",
        ):
            self.assertIn(marker, _OBSERVATION_SCRIPT)

    def test_semantic_signature_changes_when_resource_identity_changes(self) -> None:
        before = [{"key": "m1", "semanticSignature": "asset-a"}]
        after = [{"key": "m1", "semanticSignature": "asset-b"}]
        self.assertNotEqual(
            _window_semantic_signature(before),
            _window_semantic_signature(after),
        )

    def test_parser_preserves_mixed_message_container_families(self) -> None:
        html = """
        <main>
          <article data-testid="conversation-turn-1">
            <div data-message-author-role="user"><div class="markdown">One</div></div>
          </article>
          <div data-message-id="message-2">
            <div data-message-author-role="assistant"><div class="markdown">Two</div></div>
          </div>
        </main>
        """
        record = ConversationParser().parse(
            html=html,
            url="https://chatgpt.com/c/mixed",
            title="Mixed",
            exported_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
        self.assertEqual([item.plain_text for item in record.messages], ["One", "Two"])
        self.assertEqual([item.role for item in record.messages], ["user", "assistant"])
        self.assertEqual(
            [item.message_id for item in record.messages],
            ["conversation-turn-1", "message-2"],
        )

    def test_parser_reads_nested_role_and_message_id_from_outer_wrapper(self) -> None:
        message = ConversationParser().parse_message_fragment(
            html=(
                '<article data-testid="conversation-turn-9">'
                '<div data-message-id="message-9" data-message-author-role="assistant">'
                '<div class="markdown">Nested</div></div></article>'
            ),
            sequence_number=1,
            conversation_id="nested",
            base_url="https://chatgpt.com/c/nested",
        )
        self.assertEqual(message.message_id, "message-9")
        self.assertEqual(message.role, "assistant")
        self.assertEqual(message.plain_text, "Nested")

    async def test_transient_observation_retry_keeps_the_same_operation(self) -> None:
        page = _FlakyObservationPage()
        manager = BrowserManager()
        with patch("src.browser.browser_manager.asyncio.sleep", new=AsyncMock()) as sleep:
            state = await manager._observe_conversation(
                page,  # type: ignore[arg-type]
                scroll_up=False,
                force_scroll=False,
            )
        self.assertEqual(page.calls, 2)
        self.assertTrue(state["documentReady"])
        sleep.assert_awaited_once()


class CheckpointInfrastructureRegressionTests(unittest.TestCase):
    def test_checkpoint_storage_failure_is_fatal_not_degraded(self) -> None:
        item = {
            "key": "message-1",
            "signature": "assistant:stable",
            "role": "assistant",
            "domIndex": 0,
            "html": (
                '<article data-message-id="message-1" '
                'data-message-author-role="assistant">'
                '<div class="markdown">Stable</div></article>'
            ),
            "text": "Stable",
            "capturedAt": "2026-08-01T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as directory:
            store = MessageCheckpointStore(
                Path(directory) / "checkpoint",
                conversation_id="conversation",
                base_url="https://chatgpt.com/c/conversation",
            )
            with patch(
                "src.core.message_checkpoint.write_json",
                side_effect=OSError("disk unavailable"),
            ):
                with self.assertRaisesRegex(
                    MessageCheckpointInfrastructureError,
                    "persist and verify checkpoint",
                ):
                    store.capture_window([item], ("message-1",), set())
            store.close()


if __name__ == "__main__":
    unittest.main()
