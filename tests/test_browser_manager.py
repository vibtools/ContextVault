from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.browser.browser_manager import (
    BrowserManager,
    BrowserProfileInUseError,
    _sidebar_conversation_title,
    resolve_launch_user_data_dir,
)
from src.models.settings import BrowserSettings


class _FakePage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.navigations: list[tuple[str, str]] = []

    async def goto(self, url: str, *, wait_until: str) -> None:
        self.navigations.append((url, wait_until))
        self.url = url


class _FakeContext:
    def __init__(self) -> None:
        self.pages = [_FakePage()]
        self.closed = False

    async def close(self) -> None:
        self.closed = True

    def is_closed(self) -> bool:
        return self.closed


class _FakeChromium:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.context = _FakeContext()
        self.launch_kwargs: dict[str, object] | None = None

    async def launch_persistent_context(self, **kwargs: object) -> _FakeContext:
        self.launch_kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.context


class _FakePlaywright:
    def __init__(self, chromium: _FakeChromium) -> None:
        self.chromium = chromium
        self.stopped = False

    async def stop(self) -> None:
        self.stopped = True


class _FakePlaywrightStarter:
    def __init__(self, playwright: _FakePlaywright) -> None:
        self.playwright = playwright

    async def start(self) -> _FakePlaywright:
        return self.playwright


class ConversationSidebarTitleTests(unittest.TestCase):
    def test_visible_sidebar_title_wins_over_accessibility_context(self) -> None:
        title = _sidebar_conversation_title(
            {
                "visibleTitle": "YGIT 05_Project-Context&Update",
                "attributeTitle": "",
                "ariaLabel": "YGIT 05_Project-Context&Update, chat in project ygit-project",
            }
        )
        self.assertEqual(title, "YGIT 05_Project-Context&Update")

    def test_project_context_is_removed_from_aria_fallback(self) -> None:
        title = _sidebar_conversation_title(
            {
                "visibleTitle": "",
                "attributeTitle": "",
                "ariaLabel": "Release Audit, chat in project ContextVault",
            }
        )
        self.assertEqual(title, "Release Audit")

    def test_visible_title_whitespace_is_compacted_without_rewriting_content(self) -> None:
        title = _sidebar_conversation_title(
            {
                "visibleTitle": "  Exact\nChat   Title  ",
                "attributeTitle": "",
                "ariaLabel": "",
            }
        )
        self.assertEqual(title, "Exact Chat Title")

    def test_full_title_attribute_wins_over_truncated_visible_text(self) -> None:
        title = _sidebar_conversation_title(
            {
                "visibleTitle": "Long production chat...",
                "attributeTitle": "Long production chat title",
                "ariaLabel": "Long production chat title, chat in project ContextVault",
            }
        )
        self.assertEqual(title, "Long production chat title")

    def test_project_context_is_removed_from_visible_title_too(self) -> None:
        title = _sidebar_conversation_title(
            {
                "visibleTitle": "Release Audit, chat in project ContextVault",
                "attributeTitle": "",
                "ariaLabel": "Release Audit, chat in project ContextVault",
            }
        )
        self.assertEqual(title, "Release Audit")


class BrowserManagerLaunchTests(unittest.TestCase):
    def test_blank_setting_uses_contextvault_managed_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            managed_root = Path(temporary) / "managed"
            with patch(
                "src.browser.browser_manager.managed_chrome_user_data_dir",
                return_value=managed_root,
            ):
                resolved, managed = resolve_launch_user_data_dir("")

            self.assertTrue(managed)
            self.assertEqual(resolved, managed_root.resolve())
            self.assertTrue(resolved.is_dir())

    def test_regular_chrome_root_is_redirected_before_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            regular_root = root / "regular" / "User Data"
            managed_root = root / "managed"
            regular_root.mkdir(parents=True)
            with (
                patch(
                    "src.browser.browser_manager.default_chrome_user_data_dir",
                    return_value=regular_root,
                ),
                patch(
                    "src.browser.browser_manager.managed_chrome_user_data_dir",
                    return_value=managed_root,
                ),
            ):
                resolved, managed = resolve_launch_user_data_dir(str(regular_root))

            self.assertTrue(managed)
            self.assertEqual(resolved, managed_root.resolve())
            self.assertNotEqual(resolved, regular_root.resolve())

    def test_explicit_non_standard_profile_root_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            custom_root = Path(temporary) / "custom-user-data"
            custom_root.mkdir()
            with patch(
                "src.browser.browser_manager.managed_chrome_user_data_dir",
                return_value=Path(temporary) / "managed",
            ):
                resolved, managed = resolve_launch_user_data_dir(str(custom_root))

            self.assertFalse(managed)
            self.assertEqual(resolved, custom_root.resolve())

    def test_missing_explicit_profile_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing_root = Path(temporary) / "missing-user-data"
            with patch(
                "src.browser.browser_manager.managed_chrome_user_data_dir",
                return_value=Path(temporary) / "managed",
            ):
                with self.assertRaisesRegex(RuntimeError, "does not exist"):
                    resolve_launch_user_data_dir(str(missing_root))

    def test_launch_uses_isolated_profile_and_navigates(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as temporary:
                managed_root = Path(temporary) / "managed"
                chromium = _FakeChromium()
                playwright = _FakePlaywright(chromium)
                manager = BrowserManager()
                settings = BrowserSettings(
                    userDataDir="",
                    profileDirectory="Default",
                    startUrl="https://chatgpt.com/",
                )
                with (
                    patch(
                        "src.browser.browser_manager.managed_chrome_user_data_dir",
                        return_value=managed_root,
                    ),
                    patch(
                        "src.browser.browser_manager.async_playwright",
                        return_value=_FakePlaywrightStarter(playwright),
                    ),
                ):
                    status = await manager.launch(settings)

                self.assertTrue(status["connected"])
                self.assertIsNotNone(chromium.launch_kwargs)
                assert chromium.launch_kwargs is not None
                self.assertEqual(
                    chromium.launch_kwargs["user_data_dir"],
                    str(managed_root.resolve()),
                )
                self.assertEqual(chromium.launch_kwargs["channel"], "chrome")
                self.assertEqual(
                    chromium.launch_kwargs["ignore_default_args"],
                    [
                        "--disable-component-extensions-with-background-pages",
                        "--disable-extensions",
                    ],
                )
                self.assertTrue((managed_root / "Default").is_dir())
                self.assertEqual(
                    chromium.context.pages[0].navigations,
                    [("https://chatgpt.com/", "domcontentloaded")],
                )
                await manager.close()

        asyncio.run(scenario())

    def test_profile_lock_does_not_fallback_to_unrelated_cdp_browser(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as temporary:
                managed_root = Path(temporary) / "managed"
                chromium = _FakeChromium(
                    error=RuntimeError("Opening in existing browser session. Profile is already in use")
                )
                playwright = _FakePlaywright(chromium)
                manager = BrowserManager()
                manager.connect_existing = AsyncMock()  # type: ignore[method-assign]
                settings = BrowserSettings(userDataDir="", profileDirectory="Default")
                with (
                    patch(
                        "src.browser.browser_manager.managed_chrome_user_data_dir",
                        return_value=managed_root,
                    ),
                    patch(
                        "src.browser.browser_manager.async_playwright",
                        return_value=_FakePlaywrightStarter(playwright),
                    ),
                ):
                    with self.assertRaises(BrowserProfileInUseError):
                        await manager.launch(settings)

                manager.connect_existing.assert_not_awaited()

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
