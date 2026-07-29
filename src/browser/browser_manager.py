"""Playwright-owned Google Chrome browser lifecycle and extraction operations."""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import platform
import re
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes, urlparse
from uuid import NAMESPACE_URL, uuid5

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)
from tenacity import retry, retry_if_exception, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.browser.selectors import CONVERSATION_LINK_SELECTOR, LOADING_SELECTOR, TITLE_SELECTORS
from src.models.conversation import ConversationListItem
from src.models.settings import BrowserSettings, PerformanceSettings
from src.utils.paths import data_directory
from src.utils.security import sanitize_filename

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[[str, float, str, int, int], None]


def _is_retryable_download_error(error: BaseException) -> bool:
    if isinstance(error, (PlaywrightTimeoutError, PlaywrightError)):
        return True
    if isinstance(error, RuntimeError):
        message = str(error).lower()
        return any(marker in message for marker in ("http 429", "http 500", "http 502", "http 503", "http 504", "temporarily", "timeout"))
    return False


class BrowserNotReadyError(RuntimeError):
    """Raised when an operation requires an unavailable browser session."""


class BrowserProfileInUseError(BrowserNotReadyError):
    """Raised when Chrome already owns the selected persistent profile."""


def _is_profile_in_use_error(error: BaseException) -> bool:
    """Return whether Playwright reports a Chrome user-data/profile lock conflict."""
    message = str(error).casefold()
    return any(
        marker in message
        for marker in (
            "opening in existing browser session",
            "profile is already in use",
            "user data directory is already in use",
            "user-data-dir is already in use",
            "process singleton",
            "processsingleton",
        )
    )


class BrowserManager:
    """Own all Playwright objects within one dedicated worker thread."""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._browser: Browser | None = None
        self._connected_over_cdp = False

    @property
    def is_connected(self) -> bool:
        """Return whether a usable context currently exists."""
        return self._context is not None

    async def launch(self, settings: BrowserSettings) -> dict[str, Any]:
        """Launch an isolated, persistent official Chrome automation profile."""
        await self.close()
        user_data_dir, managed_profile = resolve_launch_user_data_dir(settings.user_data_dir)
        profile_path = user_data_dir / settings.profile_directory

        if managed_profile:
            profile_path.mkdir(parents=True, exist_ok=True)
        elif not profile_path.is_dir():
            raise BrowserNotReadyError(f"Chrome profile directory does not exist: {profile_path}")

        self._playwright = await async_playwright().start()
        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                channel="chrome",
                headless=False,
                args=[f"--profile-directory={settings.profile_directory}"],
                ignore_default_args=[
                    "--disable-component-extensions-with-background-pages",
                    "--disable-extensions",
                ],
                accept_downloads=True,
                viewport=None,
                no_viewport=True,
            )
            self._connected_over_cdp = False
            page = await self._select_page(create_if_missing=True)
            if page.url in {"about:blank", "chrome://newtab/"}:
                await page.goto(settings.start_url, wait_until="domcontentloaded")
            LOGGER.info(
                "Google Chrome launched with %s profile %s at %s",
                "ContextVault-managed" if managed_profile else "custom",
                settings.profile_directory,
                user_data_dir,
            )
            return await self.status()
        except Exception as error:
            profile_in_use = _is_profile_in_use_error(error)
            await self.close()
            if not profile_in_use:
                raise
            raise BrowserProfileInUseError(
                "The Chrome automation profile is already open in another Chrome or ContextVault "
                f"process: {user_data_dir}. Close that separate automation window and click Launch "
                "Chrome again. ContextVault will not attach to or modify your regular Chrome session."
            ) from error

    async def connect_existing(self, endpoint: str, timeout: float = 30_000.0) -> dict[str, Any]:
        """Connect to Chrome started with a remote-debugging endpoint."""
        await self.close()
        self._playwright = await async_playwright().start()
        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(
                endpoint,
                no_defaults=True,
                timeout=timeout,
            )
            if not self._browser.contexts:
                raise BrowserNotReadyError("The connected Chrome instance exposes no browser context.")
            self._context = self._browser.contexts[0]
            self._connected_over_cdp = True
            LOGGER.info("Connected to existing Chrome at %s", endpoint)
            return await self.status()
        except Exception:
            await self.close()
            raise

    async def close(self) -> dict[str, Any]:
        """Close Playwright-owned resources without forcefully terminating external Chrome."""
        context, browser, playwright = self._context, self._browser, self._playwright
        self._context = None
        self._browser = None
        self._playwright = None
        try:
            if context is not None and not self._connected_over_cdp:
                await context.close()
            elif browser is not None and self._connected_over_cdp:
                await browser.close()
        finally:
            self._connected_over_cdp = False
            if playwright is not None:
                await playwright.stop()
        LOGGER.info("Browser session closed")
        return await self.status()

    async def status(self) -> dict[str, Any]:
        """Return safe browser status without exposing profile/session secrets."""
        pages = list(self._context.pages) if self._context is not None else []
        active_url = pages[-1].url if pages else ""
        connected = self._context is not None and not self._context.is_closed()
        return {
            "connected": connected,
            "pageCount": len(pages),
            "activeUrl": active_url,
            "activeChat": bool(re.search(r"/(?:c|conversation)/", active_url)),
            "connectionMode": "cdp" if self._connected_over_cdp else "persistentProfile",
        }

    @retry(
        retry=retry_if_exception_type((PlaywrightTimeoutError, PlaywrightError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        reraise=True,
    )
    async def scan_conversations(
        self,
        *,
        cancellation_event: threading.Event | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> list[ConversationListItem]:
        """Scan the complete lazy-loaded sidebar and return a deduplicated list."""
        page = await self._select_page()
        await page.wait_for_load_state("domcontentloaded")
        await page.evaluate(
            """
            selector => {
                const links = Array.from(document.querySelectorAll(selector));
                const anchor = links[0] || document.querySelector('nav, aside');
                let node = anchor;
                while (node && node !== document.body) {
                    const style = getComputedStyle(node);
                    if (node.scrollHeight > node.clientHeight + 20 && /(auto|scroll)/.test(style.overflowY)) {
                        node.scrollTop = 0;
                        node.dispatchEvent(new Event('scroll', {bubbles: true}));
                        return;
                    }
                    node = node.parentElement;
                }
            }
            """,
            CONVERSATION_LINK_SELECTOR,
        )
        await page.wait_for_timeout(300)

        discovered: dict[str, dict[str, str]] = {}
        stable_rounds = 0
        previous_position = -1
        for iteration in range(1, 301):
            if cancellation_event is not None and cancellation_event.is_set():
                raise InterruptedError("Conversation scan cancelled.")
            state = await page.evaluate(
                """
                selector => {
                    const links = Array.from(document.querySelectorAll(selector));
                    const items = links.map(element => ({
                        href: element.href || element.getAttribute('href') || '',
                        title: (
                            element.getAttribute('aria-label') ||
                            element.getAttribute('title') ||
                            element.innerText ||
                            element.textContent ||
                            ''
                        ).trim()
                    }));
                    const anchor = links[0] || document.querySelector('nav, aside');
                    let scroller = null;
                    let node = anchor;
                    while (node && node !== document.body) {
                        const style = getComputedStyle(node);
                        if (node.scrollHeight > node.clientHeight + 20 && /(auto|scroll)/.test(style.overflowY)) {
                            scroller = node;
                            break;
                        }
                        node = node.parentElement;
                    }
                    scroller = scroller || document.scrollingElement || document.documentElement;
                    const before = scroller.scrollTop;
                    const step = Math.max(250, Math.floor(scroller.clientHeight * 0.8));
                    scroller.scrollTop = Math.min(scroller.scrollHeight, before + step);
                    scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
                    return {
                        items,
                        before,
                        after: scroller.scrollTop,
                        scrollHeight: scroller.scrollHeight,
                        clientHeight: scroller.clientHeight,
                        atBottom: scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 2
                    };
                }
                """,
                CONVERSATION_LINK_SELECTOR,
            )
            before_count = len(discovered)
            for item in state.get("items", []):
                if not isinstance(item, dict):
                    continue
                url = str(item.get("href") or "").strip()
                if url:
                    discovered[url] = {"href": url, "title": str(item.get("title") or "").strip()}
            position = int(state.get("after", 0))
            no_growth = len(discovered) == before_count
            if bool(state.get("atBottom")) and no_growth and position == previous_position:
                stable_rounds += 1
            else:
                stable_rounds = 0
            previous_position = position
            if progress_callback is not None:
                percentage = min(95.0, iteration / 300 * 100.0)
                progress_callback("Scanning conversations", percentage, f"{len(discovered)} found", len(discovered), len(discovered))
            if stable_rounds >= 4:
                break
            await page.wait_for_timeout(250)

        output: list[ConversationListItem] = []
        for item in discovered.values():
            url = item["href"]
            match = re.search(r"/(?:c|conversation)/([^/?#]+)", url)
            conversation_id = match.group(1) if match else str(uuid5(NAMESPACE_URL, url))
            title = item["title"] or f"Conversation {len(output) + 1}"
            output.append(ConversationListItem(conversation_id=conversation_id, title=title, url=url))
        if progress_callback is not None:
            progress_callback("Scan complete", 100.0, f"{len(output)} conversations", len(output), len(output))
        LOGGER.info("Conversation scan completed: %s found", len(output))
        return output

    @retry(
        retry=retry_if_exception_type((PlaywrightTimeoutError, PlaywrightError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        reraise=True,
    )
    async def open_conversation(self, url: str) -> dict[str, Any]:
        """Navigate the active page to a conversation URL."""
        if not url.startswith(("https://", "http://")):
            raise ValueError("Conversation URL must use HTTP or HTTPS.")
        page = await self._select_page(create_if_missing=True)
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)
        return {"url": page.url, "title": await self._page_title(page)}

    @retry(
        retry=retry_if_exception_type((PlaywrightTimeoutError, PlaywrightError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        reraise=True,
    )
    async def load_complete_conversation(
        self,
        *,
        performance: PerformanceSettings,
        cancellation_event: threading.Event,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Auto-scroll upward until lazy-loaded message state becomes stable."""
        page = await self._select_page()
        delay_ms = {"Auto": 700, "Fast": 300, "Normal": 700, "Safe": 1300}[performance.delay_mode]
        max_iterations = {"Low": 120, "Balanced": 300, "High": 800}[performance.memory_mode]
        stable_rounds = 0
        previous_count = -1
        highest_count = 0

        for iteration in range(1, max_iterations + 1):
            if cancellation_event.is_set():
                raise InterruptedError("Conversation loading cancelled.")
            state = await page.evaluate(
                """
                () => {
                    const selectors = [
                        '[data-message-author-role]',
                        '[data-testid^="conversation-turn"]'
                    ];
                    let messageCount = 0;
                    for (const selector of selectors) {
                        messageCount = Math.max(messageCount, document.querySelectorAll(selector).length);
                    }
                    const messages = Array.from(document.querySelectorAll('[data-message-author-role], [data-testid^="conversation-turn"]'));
                    let scroller = null;
                    let node = messages[0] || document.querySelector('main, [role="main"]');
                    while (node && node !== document.body) {
                        const style = getComputedStyle(node);
                        if (node.scrollHeight > node.clientHeight + 100 && /(auto|scroll)/.test(style.overflowY)) {
                            scroller = node;
                            break;
                        }
                        node = node.parentElement;
                    }
                    scroller = scroller || document.querySelector('main, [role="main"]') || document.scrollingElement || document.documentElement;
                    const before = scroller.scrollTop;
                    scroller.scrollTop = 0;
                    scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
                    return {
                        messageCount,
                        before,
                        after: scroller.scrollTop,
                        scrollHeight: scroller.scrollHeight,
                        clientHeight: scroller.clientHeight
                    };
                }
                """
            )
            count = int(state.get("messageCount", 0))
            highest_count = max(highest_count, count)
            loading = await page.locator(LOADING_SELECTOR).count()
            if count == previous_count and int(state.get("after", 0)) == 0 and loading == 0:
                stable_rounds += 1
            else:
                stable_rounds = 0
            previous_count = count
            percentage = min(95.0, (iteration / max_iterations) * 100.0)
            if progress_callback is not None:
                progress_callback("Loading messages", percentage, f"{count} messages", count, max(highest_count, count))
            if stable_rounds >= 4:
                break
            await page.wait_for_timeout(delay_ms)

        await page.wait_for_timeout(delay_ms)
        html = await page.content()
        title = await self._page_title(page)
        if progress_callback is not None:
            progress_callback("Conversation loaded", 100.0, title, highest_count, highest_count)
        return {
            "html": html,
            "url": page.url,
            "title": title,
            "messageCount": highest_count,
        }

    @retry(
        retry=retry_if_exception(_is_retryable_download_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        reraise=True,
    )
    async def download_resource(self, source_url: str) -> dict[str, Any]:
        """Download an authenticated HTTP, data, or blob resource."""
        if source_url.startswith("data:"):
            media_type, data = decode_data_url(source_url)
            return {"content": data, "contentType": media_type, "suggestedFilename": "asset"}
        if source_url.startswith("blob:"):
            page = await self._select_page()
            payload = await page.evaluate(
                """
                async url => {
                    const response = await fetch(url);
                    if (!response.ok) throw new Error(`Blob fetch failed: ${response.status}`);
                    const blob = await response.blob();
                    const bytes = new Uint8Array(await blob.arrayBuffer());
                    let binary = '';
                    const chunk = 0x8000;
                    for (let i = 0; i < bytes.length; i += chunk) {
                        binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
                    }
                    return {base64: btoa(binary), type: blob.type || ''};
                }
                """,
                source_url,
            )
            return {
                "content": base64.b64decode(payload["base64"]),
                "contentType": str(payload.get("type") or ""),
                "suggestedFilename": "asset",
            }
        if not source_url.startswith(("https://", "http://")):
            raise ValueError(f"Unsupported resource URL scheme: {source_url}")
        context = self._require_context()
        response = await context.request.get(source_url, timeout=60_000)
        if not response.ok:
            raise RuntimeError(f"Resource download failed with HTTP {response.status}: {source_url}")
        headers = response.headers
        content_type = headers.get("content-type", "").split(";", 1)[0].strip()
        filename = _filename_from_headers(headers.get("content-disposition", "")) or Path(urlparse(source_url).path).name or "asset"
        return {
            "content": await response.body(),
            "contentType": content_type,
            "suggestedFilename": sanitize_filename(filename),
        }

    @retry(
        retry=retry_if_exception_type((PlaywrightTimeoutError, PlaywrightError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        reraise=True,
    )
    async def refresh(self) -> dict[str, Any]:
        """Reload the active browser page."""
        page = await self._select_page()
        await page.reload(wait_until="domcontentloaded")
        return {"url": page.url, "title": await self._page_title(page)}

    async def _select_page(self, *, create_if_missing: bool = False) -> Page:
        context = self._require_context()
        pages = list(context.pages)
        chat_pages = [page for page in pages if re.search(r"chatgpt\.com|chat\.openai\.com", page.url)]
        if chat_pages:
            return chat_pages[-1]
        if pages:
            return pages[-1]
        if create_if_missing:
            return await context.new_page()
        raise BrowserNotReadyError("No browser page is available.")

    async def _page_title(self, page: Page) -> str:
        for selector in TITLE_SELECTORS:
            if selector == "title":
                value = await page.title()
            else:
                locator = page.locator(selector).first
                value = await locator.inner_text() if await locator.count() else ""
            value = value.strip()
            if value and value.lower() not in {"chatgpt", "new chat"}:
                return value
        return "Untitled Conversation"

    def _require_context(self) -> BrowserContext:
        if self._context is None:
            raise BrowserNotReadyError("Google Chrome is not connected.")
        return self._context


def managed_chrome_user_data_dir() -> Path:
    """Return ContextVault's persistent, non-standard Chrome user-data directory."""
    return data_directory() / "chrome-user-data"


def resolve_launch_user_data_dir(configured_path: str) -> tuple[Path, bool]:
    """Resolve a safe launch root and report whether ContextVault owns it.

    Chrome and Playwright cannot safely automate the user's regular Chrome data
    directory. A blank setting therefore selects ContextVault's own persistent
    directory. An explicitly configured regular Chrome root is also redirected
    to that managed directory so Launch Chrome never forwards a tab into the
    user's already-running daily browser.
    """
    configured = configured_path.strip()
    managed = managed_chrome_user_data_dir().resolve()
    if not configured:
        managed.mkdir(parents=True, exist_ok=True)
        return managed, True

    selected = Path(configured).expanduser().resolve()
    if _same_path(selected, managed):
        managed.mkdir(parents=True, exist_ok=True)
        return managed, True

    try:
        regular_chrome_root = default_chrome_user_data_dir()
    except BrowserNotReadyError:
        regular_chrome_root = None
    if regular_chrome_root is not None and _same_path(selected, regular_chrome_root):
        managed.mkdir(parents=True, exist_ok=True)
        LOGGER.warning(
            "The configured Chrome root %s is the regular Chrome data directory and cannot be "
            "automated safely; using ContextVault-managed profile root %s instead",
            selected,
            managed,
        )
        return managed, True

    if not selected.is_dir():
        raise BrowserNotReadyError(f"Chrome user-data directory does not exist: {selected}")
    return selected, False


def _same_path(left: Path, right: Path) -> bool:
    """Compare paths safely across case-insensitive filesystems and aliases."""
    try:
        if left.exists() and right.exists() and os.path.samefile(left, right):
            return True
    except OSError:
        pass
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def default_chrome_user_data_dir() -> Path:
    """Return the conventional regular Chrome user-data directory for detection only."""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            raise BrowserNotReadyError("LOCALAPPDATA is unavailable; select a custom Chrome user-data folder manually.")
        return Path(base) / "Google" / "Chrome" / "User Data"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    return Path.home() / ".config" / "google-chrome"


def decode_data_url(value: str) -> tuple[str, bytes]:
    """Decode a standards-compliant data URL."""
    header, separator, payload = value.partition(",")
    if not separator or not header.startswith("data:"):
        raise ValueError("Invalid data URL.")
    metadata = header[5:]
    parts = metadata.split(";") if metadata else []
    media_type = parts[0] if parts and "/" in parts[0] else "text/plain"
    if "base64" in parts[1:] or (parts and parts[-1] == "base64"):
        return media_type, base64.b64decode(payload, validate=True)
    return media_type, unquote_to_bytes(payload)


def extension_for_media_type(media_type: str, fallback: str = ".bin") -> str:
    """Return a safe filename extension for a media type."""
    guessed = mimetypes.guess_extension(media_type, strict=False)
    return guessed or fallback


def _filename_from_headers(content_disposition: str) -> str:
    match = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", content_disposition, re.IGNORECASE)
    return match.group(1).strip() if match else ""
