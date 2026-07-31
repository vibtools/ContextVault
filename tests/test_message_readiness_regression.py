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
    _OBSERVATION_SCRIPT,
    _ReadinessPolicy,
)
from src.core.export_pipeline import ExportPipeline, _merge_capture_warnings
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
        self.reload_count = 0
        self.scroll_requests = 0
        self.url = "https://chatgpt.com/g/g-p-test/c/conversation-id"

    async def evaluate(self, script: str, _payload: object | None = None) -> object:
        if isinstance(_payload, dict) and bool(_payload.get("scrollUp")):
            self.scroll_requests += 1
        if "delete window.__contextVaultObservationV2" in script:
            return None
        if self._index < len(self._states):
            value = self._states[self._index]
            self._index += 1
            return dict(value)
        return dict(self._states[-1])

    async def reload(self, *, wait_until: str) -> None:
        if wait_until != "domcontentloaded":
            raise AssertionError(f"Unexpected reload state: {wait_until}")
        self.reload_count += 1

    def locator(self, selector: str) -> _HeadLocator:
        if selector != "head":
            raise AssertionError(f"Unexpected locator: {selector}")
        return _HeadLocator()



class _ManualClock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class _AdvancingFakePage(_FakePage):
    def __init__(self, states: list[dict[str, object]], clock: _ManualClock) -> None:
        super().__init__(states)
        self._clock = clock

    async def evaluate(self, script: str, payload: object | None = None) -> object:
        if "delete window.__contextVaultObservationV2" not in script:
            self._clock.advance(0.6)
        return await super().evaluate(script, payload)


def _message(key: str, text: str, index: int) -> dict[str, object]:
    return {
        "key": key,
        "signature": f"assistant:{key}",
        "role": "assistant",
        "fallback": False,
        "domIndex": index,
        "documentTop": index * 100,
        "html": (
            f'<article data-testid="{key}" data-message-author-role="assistant">'
            f'<div class="markdown">{text}</div></article>'
        ),
        "imageCount": 0,
        "pendingImages": 0,
        "attachmentCount": 0,
        "codeBlockCount": 0,
        "tableCount": 0,
    }


def _state(
    *,
    messages: list[dict[str, object]],
    title: str = "Project Conversation",
    at_top: bool = True,
    before_scroll_top: int = 0,
    after_scroll_top: int | None = None,
    scroll_height: int = 1000,
) -> dict[str, object]:
    if after_scroll_top is None:
        after_scroll_top = before_scroll_top
    image_count = sum(max(0, int(item.get("imageCount", 0))) for item in messages)
    image_loading_count = sum(
        max(0, int(item.get("imageLoadingCount", 0))) for item in messages
    )
    pending_images = sum(
        max(
            0,
            int(item.get("pendingImages", 0)),
            int(item.get("imageLoadingCount", 0)),
        )
        for item in messages
    )
    return {
        "documentReady": True,
        "appReady": True,
        "conversationContainer": True,
        "messageCount": len(messages),
        "messages": messages,
        "mutationRevision": 0,
        "mutationIdleMs": 1000,
        "beforeScrollTop": before_scroll_top,
        "afterScrollTop": after_scroll_top,
        "scrollHeight": scroll_height,
        "clientHeight": 800,
        "atTop": at_top,
        "streaming": False,
        "continueRequired": False,
        "loadingCount": 0,
        "imageLoadingCount": image_loading_count,
        "imageCount": image_count,
        "pendingImages": pending_images,
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
        if command == "status":
            future.set_result({"connected": True})
        elif command == "open_conversation":
            future.set_result({"url": kwargs["url"], "title": "ChatGPT"})
        elif command == "load_complete_conversation":
            future.set_result(
                {
                    "html": "<!doctype html><html><head><title>ChatGPT</title></head><body><main></main></body></html>",
                    "url": "https://chatgpt.com/g/g-p-test/c/conversation-id",
                    "title": "Project Conversation",
                    "messageCount": 0,
                    "browserName": "Google Chrome",
                    "browserVersion": "138.0",
                    "browserProfile": "Default",
                    "readiness": {
                        "documentReady": True,
                        "reactReady": True,
                        "conversationContainer": True,
                        "messageCount": 0,
                        "streamingComplete": True,
                        "lazyLoadingComplete": True,
                        "imagesReady": True,
                        "incrementalVerification": True,
                        "checkpointedMessages": 0,
                    },
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

    async def test_meaningful_scan_progress_can_exceed_the_stall_timeout(self) -> None:
        clock = _ManualClock()
        newest = _message("conversation-turn-3", "Newest", 0)
        middle = _message("conversation-turn-2", "Middle", 0)
        oldest = _message("conversation-turn-1", "Oldest", 0)
        lower = _state(
            messages=[newest],
            at_top=False,
            before_scroll_top=1200,
            scroll_height=2000,
        )
        lower_scroll = _state(
            messages=[newest],
            at_top=False,
            before_scroll_top=1200,
            after_scroll_top=600,
            scroll_height=2000,
        )
        middle_window = _state(
            messages=[middle, newest],
            at_top=False,
            before_scroll_top=600,
            scroll_height=2400,
        )
        middle_scroll = _state(
            messages=[middle, newest],
            at_top=True,
            before_scroll_top=600,
            after_scroll_top=0,
            scroll_height=2400,
        )
        top = _state(
            messages=[oldest, middle, newest],
            at_top=True,
            before_scroll_top=0,
            scroll_height=2800,
        )
        page = _AdvancingFakePage(
            [lower, lower, lower_scroll, middle_window, middle_window, middle_scroll, top, top, top],
            clock,
        )
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]
        policy = _ReadinessPolicy(
            timeout_seconds=1.0,
            stability_window_seconds=0.0,
            minimum_stable_observations=1,
            initial_poll_seconds=0.001,
            maximum_poll_seconds=0.002,
        )

        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=policy),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="138.0.0.0")),
            patch("src.browser.browser_manager._monotonic", side_effect=clock.monotonic),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(),
                cancellation_event=threading.Event(),
            )

        self.assertGreater(clock.value, policy.timeout_seconds)
        self.assertEqual(loaded["messageCount"], 3)
        self.assertTrue(loaded["readiness"]["lazyLoadingComplete"])
        self.assertIn("conversation-turn-1", loaded["html"])


    async def test_stalled_image_is_bounded_and_does_not_block_virtualized_scroll(self) -> None:
        clock = _ManualClock()
        newest = _message("conversation-turn-2", "Newest with image", 0)
        newest["html"] = (
            '<article data-testid="conversation-turn-2" data-message-author-role="assistant">'
            '<div class="markdown">Newest with image<img src="https://example.test/image.png"></div>'
            '</article>'
        )
        newest["imageCount"] = 1
        newest["pendingImages"] = 1
        newest["text"] = "Newest with image"
        newest_step_2 = dict(newest)
        newest_step_2["html"] = str(newest["html"]).replace(
            "</article>", '<span data-spinner-step="2"></span></article>'
        )
        newest_step_3 = dict(newest)
        newest_step_3["html"] = str(newest["html"]).replace(
            "</article>", '<span data-spinner-step="3"></span></article>'
        )
        oldest = _message("conversation-turn-1", "Oldest", 0)
        lower_1 = _state(
            messages=[newest],
            at_top=False,
            before_scroll_top=1200,
            scroll_height=2200,
        )
        lower_1["mutationRevision"] = 1
        lower_2 = _state(
            messages=[newest_step_2],
            at_top=False,
            before_scroll_top=1200,
            scroll_height=2200,
        )
        lower_2["mutationRevision"] = 2
        lower_3 = _state(
            messages=[newest_step_3],
            at_top=False,
            before_scroll_top=1200,
            scroll_height=2200,
        )
        lower_3["mutationRevision"] = 3
        lower_scroll = _state(
            messages=[newest_step_3],
            at_top=False,
            before_scroll_top=1200,
            after_scroll_top=500,
            scroll_height=2200,
        )
        top = _state(
            messages=[oldest, newest_step_3],
            at_top=True,
            before_scroll_top=0,
            scroll_height=2600,
        )
        page = _AdvancingFakePage(
            [lower_1, lower_2, lower_3, lower_scroll, top, top, top],
            clock,
        )
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]
        policy = _ReadinessPolicy(
            timeout_seconds=10.0,
            stability_window_seconds=0.0,
            minimum_stable_observations=1,
            initial_poll_seconds=0.001,
            maximum_poll_seconds=0.002,
            image_render_grace_seconds=1.0,
        )

        checkpointed: set[str] = set()

        def checkpoint(
            items: list[dict[str, object]],
            _order: tuple[str, ...],
            _degraded: set[str],
        ) -> dict[str, object]:
            keys = [str(item.get("key") or "") for item in items if item.get("key")]
            checkpointed.update(keys)
            return {"verifiedKeys": keys, "skippedKeys": [], "failed": {}}

        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=policy),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="138.0.0.0")),
            patch("src.browser.browser_manager._monotonic", side_effect=clock.monotonic),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(),
                cancellation_event=threading.Event(),
                message_checkpoint_callback=checkpoint,
            )

        self.assertEqual(page.scroll_requests, 1)
        self.assertEqual(checkpointed, {"conversation-turn-1", "conversation-turn-2"})
        self.assertEqual(loaded["messageCount"], 2)
        self.assertTrue(loaded["readiness"]["imagesReady"])
        self.assertEqual(loaded["readiness"]["stalledImageCount"], 1)
        self.assertEqual(loaded["readiness"]["unresolvedPendingImages"], 0)
        self.assertTrue(loaded["captureWarnings"])
        self.assertIn("archive asset download", loaded["captureWarnings"][0])


    async def test_image_spinner_without_rendered_img_is_bounded_instead_of_blocking_scroll(self) -> None:
        clock = _ManualClock()
        placeholder = _message("conversation-turn-2", "Image placeholder", 0)
        placeholder["html"] = (
            '<article data-testid="conversation-turn-2" data-message-author-role="assistant">'
            '<div class="image-placeholder"><span role="progressbar"></span></div>'
            '</article>'
        )
        placeholder["imageCount"] = 0
        placeholder["pendingImages"] = 0
        placeholder["imageLoadingCount"] = 1
        placeholder["text"] = "Image placeholder"
        oldest = _message("conversation-turn-1", "Oldest", 0)
        lower = _state(
            messages=[placeholder],
            at_top=False,
            before_scroll_top=900,
            scroll_height=1800,
        )
        lower_scroll = _state(
            messages=[placeholder],
            at_top=False,
            before_scroll_top=900,
            after_scroll_top=0,
            scroll_height=1800,
        )
        top = _state(messages=[oldest, placeholder], at_top=True, scroll_height=2200)
        page = _AdvancingFakePage(
            [lower, lower, lower, lower_scroll, top, top, top],
            clock,
        )
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]
        policy = _ReadinessPolicy(
            timeout_seconds=10.0,
            stability_window_seconds=0.0,
            minimum_stable_observations=1,
            initial_poll_seconds=0.001,
            maximum_poll_seconds=0.002,
            image_render_grace_seconds=1.0,
        )

        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=policy),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="138.0.0.0")),
            patch("src.browser.browser_manager._monotonic", side_effect=clock.monotonic),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(),
                cancellation_event=threading.Event(),
            )

        self.assertEqual(page.scroll_requests, 1)
        self.assertEqual(loaded["messageCount"], 2)
        self.assertEqual(loaded["readiness"]["stalledImageCount"], 1)
        self.assertTrue(loaded["captureWarnings"])

    def test_observer_separates_image_spinners_from_blocking_chat_loaders(self) -> None:
        self.assertIn("imageLoadingElements", _OBSERVATION_SCRIPT)
        self.assertIn("blockingLoadingElements", _OBSERVATION_SCRIPT)
        self.assertNotIn("&& pendingImages === 0", _OBSERVATION_SCRIPT)

    async def test_image_that_resolves_within_grace_keeps_strict_wait_without_warning(self) -> None:
        clock = _ManualClock()
        pending = _message("conversation-turn-2", "Pending image", 0)
        pending["imageCount"] = 1
        pending["pendingImages"] = 1
        resolved = dict(pending)
        resolved["pendingImages"] = 0
        oldest = _message("conversation-turn-1", "Oldest", 0)
        lower_pending = _state(
            messages=[pending],
            at_top=False,
            before_scroll_top=1000,
            scroll_height=2000,
        )
        lower_resolved = _state(
            messages=[resolved],
            at_top=False,
            before_scroll_top=1000,
            scroll_height=2000,
        )
        lower_scroll = _state(
            messages=[resolved],
            at_top=False,
            before_scroll_top=1000,
            after_scroll_top=0,
            scroll_height=2000,
        )
        top = _state(messages=[oldest, resolved], at_top=True, scroll_height=2400)
        page = _AdvancingFakePage(
            [lower_pending, lower_resolved, lower_resolved, lower_scroll, top, top, top],
            clock,
        )
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]
        policy = _ReadinessPolicy(
            timeout_seconds=10.0,
            stability_window_seconds=0.0,
            minimum_stable_observations=1,
            initial_poll_seconds=0.001,
            maximum_poll_seconds=0.002,
            image_render_grace_seconds=5.0,
        )

        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=policy),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="138.0.0.0")),
            patch("src.browser.browser_manager._monotonic", side_effect=clock.monotonic),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(),
                cancellation_event=threading.Event(),
            )

        self.assertEqual(page.scroll_requests, 1)
        self.assertEqual(loaded["readiness"]["stalledImageCount"], 0)
        self.assertEqual(loaded["captureWarnings"], [])

    def test_capture_warning_merge_is_ordered_and_deduplicated(self) -> None:
        self.assertEqual(
            _merge_capture_warnings(
                ["checkpoint warning", "duplicate"],
                ["duplicate", "image warning", ""],
            ),
            ["checkpoint warning", "duplicate", "image warning"],
        )

    async def test_idle_empty_dom_reloads_once_then_recovers_messages(self) -> None:
        clock = _ManualClock()
        empty = _state(messages=[], title="ChatGPT")
        ready = _state(messages=[_message("conversation-turn-1", "Recovered", 0)])
        page = _AdvancingFakePage([empty, empty, empty, ready, ready, ready], clock)
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]
        policy = _ReadinessPolicy(
            timeout_seconds=10.0,
            stability_window_seconds=0.0,
            minimum_stable_observations=1,
            initial_poll_seconds=0.001,
            maximum_poll_seconds=0.002,
            empty_state_recovery_seconds=1.0,
        )

        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=policy),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="138.0.0.0")),
            patch("src.browser.browser_manager._monotonic", side_effect=clock.monotonic),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(),
                cancellation_event=threading.Event(),
            )

        self.assertEqual(page.reload_count, 1)
        self.assertEqual(loaded["messageCount"], 1)
        self.assertEqual(loaded["readiness"]["emptyStateReloads"], 1)

    async def test_idle_empty_dom_fails_after_one_bounded_recovery_reload(self) -> None:
        clock = _ManualClock()
        empty = _state(messages=[], title="ChatGPT")
        page = _AdvancingFakePage([empty], clock)
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]
        policy = _ReadinessPolicy(
            timeout_seconds=10.0,
            stability_window_seconds=0.0,
            minimum_stable_observations=1,
            initial_poll_seconds=0.001,
            maximum_poll_seconds=0.002,
            empty_state_recovery_seconds=1.0,
        )

        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=policy),
            patch("src.browser.browser_manager._monotonic", side_effect=clock.monotonic),
        ):
            with self.assertRaisesRegex(
                ConversationReadinessError,
                "after one automatic recovery reload",
            ):
                await manager.load_complete_conversation(
                    performance=PerformanceSettings(),
                    cancellation_event=threading.Event(),
                )

        self.assertEqual(page.reload_count, 1)

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
            with self.assertRaisesRegex(RuntimeError, "without any accumulated messages"):
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
