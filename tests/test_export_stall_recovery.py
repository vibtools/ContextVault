from __future__ import annotations

import threading
import unittest
from unittest.mock import AsyncMock, patch

from src.browser.browser_manager import (
    BrowserManager,
    _OBSERVATION_SCRIPT,
    _ReadinessPolicy,
    _readiness_timeout_message,
)
from src.models.settings import PerformanceSettings


class _HeadLocator:
    async def inner_html(self) -> str:
        return "<meta charset='utf-8'>"


class _Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def advance(self, seconds: float = 0.6) -> None:
        self.value += seconds


class _Page:
    def __init__(self, states: list[dict[str, object]], clock: _Clock) -> None:
        self.states = list(states)
        self.clock = clock
        self.index = 0
        self.reload_count = 0
        self.scroll_requests = 0
        self.force_scroll_requests = 0
        self.url = "https://chatgpt.com/c/stall-regression"

    async def evaluate(self, script: str, payload: object | None = None) -> object:
        if "delete window.__contextVaultObservationV2" in script:
            return None
        self.clock.advance()
        if isinstance(payload, dict) and bool(payload.get("scrollUp")):
            self.scroll_requests += 1
            if bool(payload.get("forceScroll")):
                self.force_scroll_requests += 1
        if self.index < len(self.states):
            state = self.states[self.index]
            self.index += 1
            return dict(state)
        return dict(self.states[-1])

    async def reload(self, *, wait_until: str) -> None:
        if wait_until != "domcontentloaded":
            raise AssertionError(wait_until)
        self.reload_count += 1

    def locator(self, selector: str) -> _HeadLocator:
        if selector != "head":
            raise AssertionError(selector)
        return _HeadLocator()


def _message(key: str, text: str) -> dict[str, object]:
    return {
        "key": key,
        "signature": f"assistant:{key}",
        "role": "assistant",
        "fallback": False,
        "domIndex": 0,
        "documentTop": 0,
        "html": (
            f'<article data-testid="{key}" data-message-author-role="assistant">'
            f'<div class="markdown">{text}</div></article>'
        ),
        "text": text,
        "timestamp": None,
        "imageCount": 0,
        "pendingImages": 0,
        "imageLoadingCount": 0,
        "attachmentCount": 0,
        "codeBlockCount": 0,
        "tableCount": 0,
    }


def _state(
    messages: list[dict[str, object]],
    *,
    at_top: bool,
    before: int,
    after: int | None = None,
    revision: int = 0,
    mutation_idle_ms: int = 1000,
    loading_count: int = 0,
    window_ready: bool = True,
    strategy: str = "none",
) -> dict[str, object]:
    if after is None:
        after = before
    return {
        "documentReady": True,
        "appReady": True,
        "conversationContainer": True,
        "messageCount": len(messages),
        "messages": messages,
        "mutationRevision": revision,
        "mutationIdleMs": mutation_idle_ms,
        "beforeScrollTop": before,
        "afterScrollTop": after,
        "scrollDelta": after - before,
        "scrollStrategy": strategy,
        "scrollHeight": 300000,
        "clientHeight": 900,
        "scrollRange": 299100,
        "scrollerIdentity": "main[role=main]",
        "atTop": at_top,
        "streaming": False,
        "continueRequired": False,
        "loadingCount": loading_count,
        "blockingLoaderDescriptors": (
            ["div[role=progressbar]"] if loading_count else []
        ),
        "imageLoadingCount": 0,
        "imageCount": 0,
        "pendingImages": 0,
        "attachmentCount": 0,
        "codeBlockCount": 0,
        "tableCount": 0,
        "title": "Stall regression",
        "model": None,
        "workspace": None,
        "accessDenied": False,
        "fallbackMessageKeys": 0,
        "windowReadyToScroll": window_ready,
        "url": "https://chatgpt.com/c/stall-regression",
    }


def _policy(**overrides: object) -> _ReadinessPolicy:
    values: dict[str, object] = {
        "timeout_seconds": 20.0,
        "stability_window_seconds": 0.0,
        "minimum_stable_observations": 1,
        "initial_poll_seconds": 0.001,
        "maximum_poll_seconds": 0.002,
        "empty_state_recovery_seconds": 5.0,
        "image_render_grace_seconds": 1.0,
        "semantic_stability_window_seconds": 1.0,
        "stall_recovery_seconds": 2.0,
        "maximum_stall_reloads": 2,
        "maximum_noop_scrolls": 2,
    }
    values.update(overrides)
    return _ReadinessPolicy(**values)


def _checkpoint(
    items: list[dict[str, object]],
    _order: tuple[str, ...],
    _skip: set[str],
) -> dict[str, object]:
    keys = [str(item["key"]) for item in items]
    return {"verifiedKeys": keys, "skippedKeys": [], "failed": {}}


class ExportStallRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_semantic_stability_scrolls_despite_permanent_dom_mutation_churn(self) -> None:
        clock = _Clock()
        newest = _message("conversation-turn-2", "Newest")
        oldest = _message("conversation-turn-1", "Oldest")
        lower_1 = _state(
            [newest],
            at_top=False,
            before=60216,
            revision=1,
            mutation_idle_ms=0,
        )
        lower_2 = _state(
            [newest],
            at_top=False,
            before=60216,
            revision=2,
            mutation_idle_ms=0,
        )
        lower_3 = _state(
            [newest],
            at_top=False,
            before=60216,
            revision=3,
            mutation_idle_ms=0,
        )
        scrolled = _state(
            [newest],
            at_top=True,
            before=60216,
            after=0,
            revision=4,
            mutation_idle_ms=0,
            strategy="step",
        )
        top = _state(
            [oldest, newest],
            at_top=True,
            before=0,
            revision=5,
            mutation_idle_ms=0,
        )
        page = _Page(
            [lower_1, lower_2, lower_3, scrolled, top, top, top],
            clock,
        )
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]

        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=_policy()),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="140.0")),
            patch("src.browser.browser_manager._monotonic", side_effect=clock.monotonic),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(),
                cancellation_event=threading.Event(),
                message_checkpoint_callback=_checkpoint,
            )

        self.assertEqual(loaded["messageCount"], 2)
        self.assertEqual(page.scroll_requests, 1)
        self.assertGreaterEqual(
            loaded["readiness"]["semanticFallbackWindows"],
            1,
        )
        self.assertEqual(loaded["readiness"]["stallReloads"], 0)

    async def test_noop_normal_scroll_uses_forced_recovery_scroll(self) -> None:
        clock = _Clock()
        newest = _message("conversation-turn-2", "Newest")
        oldest = _message("conversation-turn-1", "Oldest")
        lower = _state([newest], at_top=False, before=1200)
        normal_noop = _state(
            [newest],
            at_top=False,
            before=1200,
            after=1200,
            strategy="step",
        )
        lower_again = _state([newest], at_top=False, before=1200)
        forced = _state(
            [newest],
            at_top=True,
            before=1200,
            after=0,
            strategy="recovery-anchor",
        )
        top = _state([oldest, newest], at_top=True, before=0)
        page = _Page(
            [
                lower,
                lower,
                normal_noop,
                lower_again,
                lower_again,
                forced,
                top,
                top,
                top,
            ],
            clock,
        )
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]

        with (
            patch("src.browser.browser_manager._readiness_policy", return_value=_policy()),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="140.0")),
            patch("src.browser.browser_manager._monotonic", side_effect=clock.monotonic),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(),
                cancellation_event=threading.Event(),
                message_checkpoint_callback=_checkpoint,
            )

        self.assertEqual(loaded["messageCount"], 2)
        self.assertGreaterEqual(page.scroll_requests, 2)
        self.assertGreaterEqual(page.force_scroll_requests, 1)
        self.assertGreaterEqual(
            loaded["readiness"]["forcedScrollAttempts"],
            1,
        )
        self.assertEqual(page.reload_count, 0)

    async def test_persistent_visible_loader_uses_semantic_recovery_scroll(self) -> None:
        clock = _Clock()
        newest = _message("conversation-turn-2", "Newest")
        oldest = _message("conversation-turn-1", "Oldest")
        blocked = _state(
            [newest],
            at_top=False,
            before=60216,
            revision=10,
            mutation_idle_ms=1000,
            loading_count=1,
            window_ready=False,
        )
        forced = _state(
            [newest],
            at_top=True,
            before=60216,
            after=0,
            strategy="recovery-anchor",
        )
        top = _state([oldest, newest], at_top=True, before=0)
        page = _Page(
            [blocked, blocked, blocked, forced, top, top, top],
            clock,
        )
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]

        with (
            patch(
                "src.browser.browser_manager._readiness_policy",
                return_value=_policy(stall_recovery_seconds=1.0),
            ),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="140.0")),
            patch("src.browser.browser_manager._monotonic", side_effect=clock.monotonic),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(),
                cancellation_event=threading.Event(),
                message_checkpoint_callback=_checkpoint,
            )

        self.assertEqual(loaded["messageCount"], 2)
        self.assertGreaterEqual(page.force_scroll_requests, 1)
        self.assertEqual(page.reload_count, 0)
        self.assertGreaterEqual(
            loaded["readiness"]["semanticFallbackWindows"],
            1,
        )

    async def test_non_settling_nonempty_window_reloads_once_and_resumes(self) -> None:
        clock = _Clock()
        newest = _message("conversation-turn-2", "Newest")
        oldest = _message("conversation-turn-1", "Oldest")
        blocked_a = _state(
            [_message("conversation-turn-2", "Changing A")],
            at_top=False,
            before=60216,
            revision=1,
            mutation_idle_ms=0,
            loading_count=1,
            window_ready=False,
        )
        blocked_b = _state(
            [_message("conversation-turn-2", "Changing B")],
            at_top=False,
            before=60216,
            revision=2,
            mutation_idle_ms=0,
            loading_count=1,
            window_ready=False,
        )
        recovered = _state([newest], at_top=False, before=900)
        recovered_again = _state([newest], at_top=False, before=900)
        scrolled = _state(
            [newest],
            at_top=True,
            before=900,
            after=0,
            strategy="step",
        )
        top = _state([oldest, newest], at_top=True, before=0)
        page = _Page(
            [
                blocked_a,
                blocked_b,
                blocked_a,
                blocked_b,
                recovered,
                recovered_again,
                scrolled,
                top,
                top,
                top,
            ],
            clock,
        )
        manager = BrowserManager()
        manager._select_page = AsyncMock(return_value=page)  # type: ignore[method-assign]

        with (
            patch(
                "src.browser.browser_manager._readiness_policy",
                return_value=_policy(stall_recovery_seconds=1.0),
            ),
            patch("src.browser.browser_manager._browser_version", AsyncMock(return_value="140.0")),
            patch("src.browser.browser_manager._monotonic", side_effect=clock.monotonic),
        ):
            loaded = await manager.load_complete_conversation(
                performance=PerformanceSettings(),
                cancellation_event=threading.Event(),
                message_checkpoint_callback=_checkpoint,
            )

        self.assertEqual(page.reload_count, 1)
        self.assertEqual(loaded["messageCount"], 2)
        self.assertEqual(loaded["readiness"]["stallReloads"], 1)

    def test_timeout_diagnostics_expose_exact_blocking_predicates(self) -> None:
        state = _state(
            [_message("conversation-turn-1", "Message")],
            at_top=False,
            before=60216,
            revision=44,
            mutation_idle_ms=0,
            loading_count=1,
            window_ready=False,
        )
        message = _readiness_timeout_message(
            state,
            109,
            0,
            _policy(),
            elapsed_seconds=1227.3,
            inactive_seconds=900.2,
            diagnostics={
                "semanticStableObservations": 90,
                "semanticStableSeconds": 45.0,
                "scrollAttempts": 4,
                "forcedScrollAttempts": 2,
                "consecutiveNoopScrolls": 2,
                "stallReloads": 2,
                "verifiedCheckpointMessages": 109,
            },
        )
        for marker in (
            "windowReadyToScroll=False",
            "loadingCount=1",
            "mutationRevision=44",
            "mutationIdleMs=0",
            "semanticStableSeconds=45.0",
            "scrollAttempts=4",
            "forcedScrollAttempts=2",
            "stallReloads=2",
            "verifiedCheckpointMessages=109",
            "blockingLoaders=div[role=progressbar]",
        ):
            self.assertIn(marker, message)

    def test_observer_has_visible_loader_filter_and_recovery_scroll_contract(self) -> None:
        self.assertIn("isElementVisible", _OBSERVATION_SCRIPT)
        self.assertIn("forceScroll", _OBSERVATION_SCRIPT)
        self.assertIn("recovery-anchor", _OBSERVATION_SCRIPT)
        self.assertIn("scrollerIdentity", _OBSERVATION_SCRIPT)
        self.assertIn("blockingLoaderDescriptors", _OBSERVATION_SCRIPT)
        self.assertIn("visibleStreamingElements", _OBSERVATION_SCRIPT)
        self.assertIn("requestAnimationFrame", _OBSERVATION_SCRIPT)


if __name__ == "__main__":
    unittest.main()
