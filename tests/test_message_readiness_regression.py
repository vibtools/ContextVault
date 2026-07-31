from __future__ import annotations

import concurrent.futures
import queue
import tempfile
import threading
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.browser.browser_manager import (
    BrowserManager,
    ConversationReadinessError,
    _ReadinessPolicy,
)
from src.core.export_pipeline import ExportPipeline
from src.core.task_manager import TaskContext
from src.models.conversation import ConversationListItem
from src.models.settings import ApplicationSettings, PerformanceSettings
from src.parsers.conversation_parser import ConversationParser


class _HeadLocator:
    async def inner_html(self) -> str:
        return "<meta charset='utf-8'>"


class _FakePage:
    def __init__(self, states: list[dict[str, object]]) -> None:
        self._states = list(states)
        self._index = 0
        self.url = "https://chatgpt.com/g/g-p-test/c/conversation-id"

    async def evaluate(self, script: str, _payload: object | None = None) -> object:
        if "delete window.__contextVaultObservationV2" in script:
            return None
        if self._index < len(self._states):
            value = self._states[self._index]
            self._index += 1
            return dict(value)
        return dict(self._states[-1])

    def locator(self, selector: str) -> _HeadLocator:
        if selector != "head":
            raise AssertionError(f"Unexpected locator: {selector}")
        return _HeadLocator()



def _state(*, messages: list[dict[str, object]], title: str = "Project Conversation") -> dict[str, object]:
    return {
        "documentReady": True,
        "appReady": True,
        "conversationContainer": True,
        "messageCount": len(messages),
        "messages": messages,
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
        "codeBlockCount": 0,
        "tableCount": 0,
        "title": title,
        "model": None,
        "workspace": None,
        "accessDenied": False,
        "fallbackMessageKeys": 0,
        "windowReadyToScroll": bool(messages),
        "url": "https://chatgpt.com/g/g-p-test/c/conversation-id",
    }




class _EmptyReadinessWorker:
    def submit(self, command: str, **kwargs: object) -> concurrent.futures.Future[object]:
        future: concurrent.futures.Future[object] = concurrent.futures.Future()
        if command == "open_conversation":
            future.set_result({"url": kwargs["url"], "title": "ChatGPT"})
        elif command == "load_complete_conversation":
            future.set_result(
                {
                    "html": "<!doctype html><html><head><title>ChatGPT</title></head><body><main></main></body></html>",
                    "url": "https://chatgpt.com/g/g-p-test/c/conversation-id",
                    "title": "Project Conversation",
                    "messageCount": 0,
                }
            )
        else:
            future.set_exception(AssertionError(f"Unexpected command: {command}"))
        return future


class ConversationReadinessRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_stable_empty_dom_never_completes_before_messages_arrive(self) -> None:
        empty = _state(messages=[], title="ChatGPT")
        message = {
            "key": "conversation-turn-1",
            "signature": "assistant:one",
            "role": "assistant",
            "fallback": False,
            "domIndex": 0,
            "documentTop": 0,
            "html": (
                '<article data-testid="conversation-turn-1" '
                'data-message-author-role="assistant"><div class="markdown">Ready</div></article>'
            ),
            "imageCount": 0,
            "pendingImages": 0,
            "attachmentCount": 0,
            "codeBlockCount": 0,
            "tableCount": 0,
        }
        ready = _state(messages=[message])
        page = _FakePage([empty, empty, empty, ready, ready, ready])
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]
        policy = _ReadinessPolicy(
            timeout_seconds=0.5,
            stability_window_seconds=0.0,
            minimum_stable_observations=1,
            initial_poll_seconds=0.001,
            maximum_poll_seconds=0.002,
        )

        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=policy),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="138.0.0.0")),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(),
                cancellation_event=threading.Event(),
            )

        self.assertEqual(loaded["messageCount"], 1)
        self.assertIn("conversation-turn-1", loaded["html"])
        self.assertTrue(loaded["readiness"]["conversationContainer"])

    async def test_permanently_empty_dom_raises_readiness_error_instead_of_returning_html(self) -> None:
        page = _FakePage([_state(messages=[], title="ChatGPT")])
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]
        policy = _ReadinessPolicy(
            timeout_seconds=0.02,
            stability_window_seconds=0.0,
            minimum_stable_observations=1,
            initial_poll_seconds=0.001,
            maximum_poll_seconds=0.002,
        )

        with patch("src.browser.browser_manager._readiness_policy", return_value=policy):
            with self.assertRaisesRegex(ConversationReadinessError, "Observed 0 message"):
                await manager.load_complete_conversation(
                    performance=PerformanceSettings(),
                    cancellation_event=threading.Event(),
                )


    def test_pipeline_rejects_zero_message_payload_before_parsing(self) -> None:
        pipeline = ExportPipeline(_EmptyReadinessWorker())  # type: ignore[arg-type]
        context = TaskContext("empty-readiness", threading.Event(), queue.Queue())
        item = ConversationListItem(
            conversationId="conversation-id",
            title="Project Conversation",
            url="https://chatgpt.com/g/g-p-test/c/conversation-id",
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "readiness did not produce any messages"):
                pipeline.export_conversation(
                    context,
                    item,
                    ApplicationSettings(),
                    Path(directory),
                )

    def test_parser_accepts_current_data_message_id_container_fallback(self) -> None:
        html = (
            "<!doctype html><html><head><title>Project chat</title></head><body><main>"
            '<div data-message-id="message-1"><div class="markdown">Loaded later</div></div>'
            "</main></body></html>"
        )
        conversation = ConversationParser().parse(
            html=html,
            url="https://chatgpt.com/g/g-p-test/c/conversation-id",
            title="Project chat",
            exported_at=datetime(2026, 7, 29, tzinfo=UTC),
        )
        self.assertEqual(len(conversation.messages), 1)
        self.assertEqual(conversation.messages[0].message_id, "message-1")
        self.assertIn("Loaded later", conversation.messages[0].plain_text)


if __name__ == "__main__":
    unittest.main()
