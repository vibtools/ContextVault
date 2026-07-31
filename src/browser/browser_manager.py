"""Playwright-owned Google Chrome browser lifecycle and extraction operations."""

from __future__ import annotations

import asyncio
import base64
import html as html_module
import logging
import mimetypes
import os
import platform
import re
import threading
import time
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, unquote_to_bytes, urlparse
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

from src.browser.selectors import (
    APPLICATION_ROOT_SELECTOR,
    CONVERSATION_CONTAINER_SELECTOR,
    CONVERSATION_LINK_SELECTOR,
    FALLBACK_MESSAGE_SELECTOR,
    LOADING_SELECTOR,
    MESSAGE_SELECTOR,
    MODEL_SELECTORS,
    PRIMARY_MESSAGE_SELECTOR,
    STREAMING_SELECTOR,
    TITLE_SELECTORS,
    WORKSPACE_SELECTORS,
)
from src.models.conversation import ConversationListItem
from src.models.settings import BrowserSettings, PerformanceSettings
from src.utils.paths import data_directory
from src.utils.security import sanitize_filename

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[[str, float, str, int, int], None]


_OBSERVATION_SCRIPT = r"""
({
    messageSelector,
    primaryMessageSelector,
    fallbackMessageSelector,
    applicationRootSelector,
    conversationContainerSelector,
    loadingSelector,
    streamingSelector,
    modelSelectors,
    workspaceSelectors,
    scrollUp
}) => {
    const stateKey = '__contextVaultObservationV2';
    const root = document.querySelector(conversationContainerSelector)
        || document.querySelector(applicationRootSelector)
        || document.body;

    const isRelevantMutation = mutation => {
        const target = mutation.target instanceof Element
            ? mutation.target
            : mutation.target && mutation.target.parentElement;
        if (!target || !root.contains(target)) return false;
        if (mutation.type === 'characterData') {
            return Boolean(target.closest(messageSelector));
        }
        if (mutation.type === 'attributes') {
            return ['src', 'href', 'aria-busy', 'data-loading', 'data-message-author-role']
                .includes(mutation.attributeName || '');
        }
        const nodes = [...mutation.addedNodes, ...mutation.removedNodes];
        return nodes.some(node => {
            if (!(node instanceof Element)) return false;
            return node.matches(messageSelector + ', img, pre, code, table, a[href]')
                || Boolean(node.querySelector(messageSelector + ', img, pre, code, table, a[href]'));
        });
    };

    let observation = window[stateKey];
    if (!observation || observation.root !== root || !observation.observer) {
        if (observation && observation.observer) observation.observer.disconnect();
        observation = {
            root,
            revision: 0,
            lastMutationAt: performance.now(),
            observer: null
        };
        observation.observer = new MutationObserver(mutations => {
            if (mutations.some(isRelevantMutation)) {
                observation.revision += 1;
                observation.lastMutationAt = performance.now();
            }
        });
        observation.observer.observe(root, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true,
            attributeFilter: ['src', 'href', 'aria-busy', 'data-loading', 'data-message-author-role']
        });
        window[stateKey] = observation;
    }

    const canonicalMessages = () => {
        const primary = Array.from(document.querySelectorAll(primaryMessageSelector));
        if (primary.length) {
            return primary.filter(node => !node.parentElement?.closest(primaryMessageSelector));
        }
        const fallback = Array.from(document.querySelectorAll(fallbackMessageSelector));
        if (fallback.length) {
            return fallback.filter(node => !node.parentElement?.closest(fallbackMessageSelector));
        }
        return Array.from(document.querySelectorAll('main article'));
    };

    const hashText = value => {
        let hash = 2166136261;
        for (let index = 0; index < value.length; index += 1) {
            hash ^= value.charCodeAt(index);
            hash = Math.imul(hash, 16777619);
        }
        return (hash >>> 0).toString(16).padStart(8, '0');
    };

    const messages = canonicalMessages();
    let scroller = null;
    let node = messages[0] || root;
    while (node && node !== document.body) {
        const style = getComputedStyle(node);
        if (node.scrollHeight > node.clientHeight + 50 && /(auto|scroll)/.test(style.overflowY)) {
            scroller = node;
            break;
        }
        node = node.parentElement;
    }
    scroller = scroller || document.scrollingElement || document.documentElement;
    const beforeScrollTop = Number(scroller.scrollTop || 0);
    const scrollHeight = Number(scroller.scrollHeight || document.documentElement.scrollHeight || 0);
    const clientHeight = Number(scroller.clientHeight || window.innerHeight || 0);
    const scrollerRect = scroller.getBoundingClientRect
        ? scroller.getBoundingClientRect()
        : {top: 0};

    const isImagePending = image => {
        const source = image.currentSrc || image.src || image.getAttribute('data-src') || '';
        if (!source || source.startsWith('data:image/svg')) return false;
        return !image.complete || image.naturalWidth === 0;
    };
    const attachmentSource = element => (
        element.getAttribute('href')
        || element.getAttribute('data-download-url')
        || element.getAttribute('data-file-url')
        || element.getAttribute('data-href')
        || element.getAttribute('data-url')
        || ''
    );
    const isAttachment = element => {
        const attributes = `${element.getAttribute('download') || ''} ${element.getAttribute('data-testid') || ''} ${element.getAttribute('aria-label') || ''} ${element.getAttribute('data-file-id') || ''} ${element.getAttribute('data-filename') || ''} ${element.getAttribute('data-file-name') || ''} ${element.className || ''}`.toLowerCase();
        const href = attachmentSource(element);
        const label = (element.innerText || element.textContent || '').trim();
        return Boolean(element.hasAttribute('download'))
            || /(attachment|download|file)/.test(attributes)
            || /(?:backend-api\/files|file-service|\/files\/)/i.test(href)
            || /\.(7z|bmp|csv|doc|docx|gif|html|jpeg|jpg|json|md|ods|odt|pdf|png|ppt|pptx|py|rar|rtf|tar|tsv|txt|webp|xls|xlsx|xml|yaml|yml|zip)(?:$|[?#])/i.test(href)
            || /\.(7z|bmp|csv|doc|docx|gif|html|jpeg|jpg|json|md|ods|odt|pdf|png|ppt|pptx|py|rar|rtf|tar|tsv|txt|webp|xls|xlsx|xml|yaml|yml|zip)$/i.test(label)
            || href.startsWith('sandbox:');
    };

    const fallbackCounts = new Map();
    const serializedMessages = messages.map((node, index) => {
        const nestedMessageId = node.querySelector('[data-message-id]')?.getAttribute('data-message-id') || '';
        const nestedTestId = node.querySelector('[data-testid^="conversation-turn"]')?.getAttribute('data-testid') || '';
        const role = (
            node.getAttribute('data-message-author-role')
            || node.querySelector('[data-message-author-role]')?.getAttribute('data-message-author-role')
            || 'unknown'
        ).trim().toLowerCase();
        const sourceKey = (
            node.getAttribute('data-message-id')
            || nestedMessageId
            || node.getAttribute('data-testid')
            || nestedTestId
            || node.id
            || ''
        ).trim();
        const text = (node.innerText || node.textContent || '').trim();
        const markup = node.outerHTML || '';
        const signature = `${role}:${hashText(text)}:${hashText(markup)}`;
        const nodeRect = node.getBoundingClientRect();
        const documentTop = Math.round(nodeRect.top - Number(scrollerRect.top || 0) + beforeScrollTop);
        let key = sourceKey;
        let fallback = false;
        if (!key) {
            fallback = true;
            const occurrence = (fallbackCounts.get(signature) || 0) + 1;
            fallbackCounts.set(signature, occurrence);
            const positionBucket = Math.round(documentTop / 128);
            key = `fallback:${signature}:${occurrence}:${positionBucket}`;
        }
        const nodeImages = Array.from(node.querySelectorAll('img'));
        const attachmentKeys = new Set();
        const nodeAttachments = Array.from(node.querySelectorAll('a[href], [data-download-url], [data-file-url], [data-href], [data-url], [data-file-id], [data-filename], [data-file-name], [data-testid*=file], [data-testid*=download], [aria-label*=Download], [aria-label*=download]'))
            .filter(isAttachment)
            .filter(element => {
                const key = `${attachmentSource(element)}|${(element.innerText || element.textContent || '').trim()}`;
                if (attachmentKeys.has(key)) return false;
                attachmentKeys.add(key);
                return true;
            });
        return {
            key,
            signature,
            role,
            fallback,
            domIndex: index,
            documentTop,
            html: markup,
            imageCount: nodeImages.length,
            pendingImages: nodeImages.filter(isImagePending).length,
            attachmentCount: nodeAttachments.length,
            codeBlockCount: node.querySelectorAll('pre code').length,
            tableCount: node.querySelectorAll('table').length
        };
    });

    const visibleText = (root.innerText || root.textContent || '').toLowerCase();
    const buttons = Array.from(root.querySelectorAll('button'));
    const continueRequired = buttons.some(button => {
        const text = `${button.innerText || ''} ${button.getAttribute('aria-label') || ''}`.toLowerCase();
        return text.includes('continue generating') || text.includes('continue response');
    });
    const stopGenerating = buttons.some(button => {
        const text = `${button.innerText || ''} ${button.getAttribute('aria-label') || ''}`.toLowerCase();
        return text.includes('stop generating');
    });
    const streaming = Boolean(document.querySelector(streamingSelector)) || stopGenerating;
    const loadingCount = document.querySelectorAll(loadingSelector).length;
    const imageCount = serializedMessages.reduce((total, item) => total + item.imageCount, 0);
    const pendingImages = serializedMessages.reduce((total, item) => total + item.pendingImages, 0);
    const attachmentCount = serializedMessages.reduce((total, item) => total + item.attachmentCount, 0);
    const codeBlockCount = serializedMessages.reduce((total, item) => total + item.codeBlockCount, 0);
    const tableCount = serializedMessages.reduce((total, item) => total + item.tableCount, 0);

    let afterScrollTop = beforeScrollTop;
    const windowReadyToScroll = document.readyState !== 'loading'
        && serializedMessages.length > 0
        && !streaming
        && !continueRequired
        && loadingCount === 0
        && pendingImages === 0;
    if (scrollUp && windowReadyToScroll && beforeScrollTop > 0) {
        const step = Math.max(600, Math.floor(clientHeight * 0.85));
        afterScrollTop = Math.max(0, beforeScrollTop - step);
        scroller.scrollTop = afterScrollTop;
        scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
    } else if (scrollUp && windowReadyToScroll && beforeScrollTop <= 1) {
        scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
    }

    const firstText = selectors => {
        for (const selector of selectors) {
            const candidate = document.querySelector(selector);
            const value = (candidate?.innerText || candidate?.textContent || candidate?.getAttribute('aria-label') || '').trim();
            if (value) return value.slice(0, 200);
        }
        return null;
    };

    const accessDenied = /you (?:do not|don't) have access|conversation (?:not found|unavailable)|unable to load conversation/.test(visibleText);
    const rootExists = Boolean(root);
    const documentReady = document.readyState === 'interactive' || document.readyState === 'complete';
    const appReady = Boolean(document.querySelector(applicationRootSelector));
    const conversationContainer = Boolean(document.querySelector(conversationContainerSelector));

    return {
        documentReady,
        appReady,
        conversationContainer,
        messageCount: serializedMessages.length,
        messages: serializedMessages,
        mutationRevision: observation.revision,
        mutationIdleMs: Math.max(0, performance.now() - observation.lastMutationAt),
        beforeScrollTop,
        afterScrollTop: Number(scroller.scrollTop || afterScrollTop),
        scrollHeight,
        clientHeight,
        atTop: Number(scroller.scrollTop || afterScrollTop) <= 1,
        streaming,
        continueRequired,
        loadingCount,
        imageCount,
        pendingImages,
        attachmentCount,
        codeBlockCount,
        tableCount,
        title: (document.querySelector('main h1, header h1')?.textContent || document.title || '').trim(),
        model: firstText(modelSelectors),
        workspace: firstText(workspaceSelectors),
        accessDenied,
        fallbackMessageKeys: serializedMessages.filter(item => item.fallback).length,
        windowReadyToScroll,
        url: location.href
    };
}
"""

_FIND_AND_SCROLL_ATTACHMENT_SCRIPT = r"""
({source, filename, fileId, messageId, token, reset}) => {
    const normalized = value => {
        try { return decodeURIComponent(String(value || '')).trim(); }
        catch (_error) { return String(value || '').trim(); }
    };
    const sourceValue = normalized(source);
    const filenameValue = normalized(filename).toLowerCase();
    const fileIdValue = normalized(fileId);
    const messageIdValue = normalized(messageId);
    const sourceAttributes = ['href', 'data-download-url', 'data-file-url', 'data-href', 'data-url'];
    const candidates = Array.from(document.querySelectorAll(
        'a[href], button, [role="button"], [data-download-url], [data-file-url], [data-href], [data-url], [data-file-id], [data-filename], [data-file-name], [data-testid*=file], [data-testid*=download], [aria-label*=Download], [aria-label*=download]'
    ));
    const matchesFile = element => {
        if (fileIdValue && normalized(element.getAttribute('data-file-id')) === fileIdValue) return true;
        if (sourceValue && normalized(element.href) === sourceValue) return true;
        for (const attribute of sourceAttributes) {
            const value = normalized(element.getAttribute(attribute));
            if (sourceValue && value === sourceValue) return true;
        }
        if (!filenameValue) return false;
        const names = [
            element.getAttribute('download'),
            element.getAttribute('data-filename'),
            element.getAttribute('data-file-name'),
            element.getAttribute('aria-label'),
            element.innerText,
            element.textContent,
        ].map(value => normalized(value).toLowerCase()).filter(Boolean);
        return names.some(value => value === filenameValue || value.includes(filenameValue));
    };
    const messageMatches = element => {
        if (!messageIdValue) return false;
        const message = element.closest('[data-message-id], [data-message-author-role], [data-testid^="conversation-turn"]');
        const observedMessageId = normalized(
            message?.getAttribute('data-message-id')
            || message?.getAttribute('data-testid')
            || ''
        );
        return Boolean(observedMessageId && observedMessageId.includes(messageIdValue));
    };
    const fileMatches = candidates.filter(matchesFile);
    const match = fileMatches.find(messageMatches) || fileMatches[0];
    if (match) {
        document.querySelectorAll('[data-contextvault-download-token]').forEach(element => {
            element.removeAttribute('data-contextvault-download-token');
        });
        match.setAttribute('data-contextvault-download-token', token);
        match.scrollIntoView({block: 'center', inline: 'nearest'});
        return {found: true, atBottom: false};
    }

    const message = document.querySelector('[data-message-id], [data-message-author-role], [data-testid^="conversation-turn"]');
    let scroller = message;
    while (scroller && scroller !== document.body) {
        const style = getComputedStyle(scroller);
        if (scroller.scrollHeight > scroller.clientHeight + 80 && /(auto|scroll)/.test(style.overflowY)) break;
        scroller = scroller.parentElement;
    }
    if (!scroller || scroller === document.body) scroller = document.scrollingElement || document.documentElement;
    if (reset) {
        scroller.scrollTop = 0;
        return {found: false, atBottom: false, scrollTop: scroller.scrollTop};
    }
    const before = scroller.scrollTop;
    const step = Math.max(420, Math.floor(scroller.clientHeight * 0.72));
    scroller.scrollTop = Math.min(scroller.scrollHeight, before + step);
    const atBottom = scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8;
    return {found: false, atBottom, scrollTop: scroller.scrollTop};
}
"""


_CLEANUP_OBSERVER_SCRIPT = r"""
() => {
    const state = window.__contextVaultObservationV2;
    if (state && state.observer) state.observer.disconnect();
    delete window.__contextVaultObservationV2;
}
"""


def _is_retryable_download_error(error: BaseException) -> bool:
    if isinstance(error, (PlaywrightTimeoutError, PlaywrightError)):
        return True
    if isinstance(error, RuntimeError):
        message = str(error).lower()
        return any(
            marker in message
            for marker in (
                "http 429",
                "http 500",
                "http 502",
                "http 503",
                "http 504",
                "temporarily",
                "timeout",
            )
        )
    return False


class BrowserNotReadyError(RuntimeError):
    """Raised when an operation requires an unavailable browser session."""


class BrowserProfileInUseError(BrowserNotReadyError):
    """Raised when Chrome already owns the selected persistent profile."""


class ConversationReadinessError(BrowserNotReadyError):
    """Raised after adaptive conversation readiness verification is exhausted."""


class ConversationUnavailableError(BrowserNotReadyError):
    """Raised when ChatGPT explicitly reports an inaccessible conversation."""


@dataclass(frozen=True, slots=True)
class _ReadinessPolicy:
    timeout_seconds: float
    stability_window_seconds: float
    minimum_stable_observations: int
    initial_poll_seconds: float
    maximum_poll_seconds: float


class _MessageAccumulator:
    """Merge overlapping virtualized DOM windows without losing message order."""

    def __init__(self) -> None:
        self._order: list[str] = []
        self._html_by_key: dict[str, str] = {}
        self._fallback_keys: set[str] = set()
        self._pending_images_by_key: dict[str, int] = {}
        self._asset_counts_by_key: dict[str, dict[str, int]] = {}

    @property
    def count(self) -> int:
        return len(self._order)

    @property
    def fallback_count(self) -> int:
        return len(self._fallback_keys)

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(self._order)

    @property
    def pending_image_count(self) -> int:
        return sum(self._pending_images_by_key.get(key, 0) for key in self._order)

    @property
    def asset_counts(self) -> dict[str, int]:
        totals = {"images": 0, "attachments": 0, "codeBlocks": 0, "tables": 0}
        for key in self._order:
            counts = self._asset_counts_by_key.get(key, {})
            for name in totals:
                totals[name] += max(0, int(counts.get(name, 0)))
        return totals

    def merge(self, messages: Iterable[dict[str, Any]]) -> bool:
        incoming: list[str] = []
        changed = False
        for item in messages:
            key = str(item.get("key") or "").strip()
            markup = str(item.get("html") or "")
            if not key or not markup or key in incoming:
                continue
            incoming.append(key)
            if bool(item.get("fallback")):
                self._fallback_keys.add(key)
            if self._html_by_key.get(key) != markup:
                self._html_by_key[key] = markup
                changed = True
            pending_images = max(0, int(item.get("pendingImages", 0)))
            if self._pending_images_by_key.get(key) != pending_images:
                self._pending_images_by_key[key] = pending_images
                changed = True
            asset_counts = {
                "images": max(0, int(item.get("imageCount", 0))),
                "attachments": max(0, int(item.get("attachmentCount", 0))),
                "codeBlocks": max(0, int(item.get("codeBlockCount", 0))),
                "tables": max(0, int(item.get("tableCount", 0))),
            }
            if self._asset_counts_by_key.get(key) != asset_counts:
                self._asset_counts_by_key[key] = asset_counts
                changed = True

        if not incoming:
            return changed
        merged = _merge_order(self._order, incoming)
        if merged != self._order:
            self._order = merged
            changed = True
        return changed

    def html_fragments(self) -> list[str]:
        return [self._html_by_key[key] for key in self._order if key in self._html_by_key]


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
        self._profile_directory = "unavailable"

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
            self._profile_directory = settings.profile_directory
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
            self._profile_directory = "external-cdp"
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
            self._profile_directory = "unavailable"
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
        await asyncio.sleep(0.2)

        discovered: dict[str, dict[str, str]] = {}
        stable_rounds = 0
        previous_position = -1
        poll_seconds = 0.1
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
                poll_seconds = min(0.8, poll_seconds * 1.4)
            else:
                stable_rounds = 0
                poll_seconds = 0.1
            previous_position = position
            if progress_callback is not None:
                percentage = min(95.0, iteration / 300 * 100.0)
                progress_callback(
                    "Scanning conversations",
                    percentage,
                    f"{len(discovered)} found",
                    len(discovered),
                    len(discovered),
                )
            if stable_rounds >= 4:
                break
            await asyncio.sleep(poll_seconds)

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
        """Navigate the active page to a conversation URL without assuming readiness."""
        if not url.startswith(("https://", "http://")):
            raise ValueError("Conversation URL must use HTTP or HTTPS.")
        page = await self._select_page(create_if_missing=True)
        await page.goto(url, wait_until="domcontentloaded")
        LOGGER.info("Conversation navigation completed; readiness observation will continue: %s", page.url)
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
        """Observe, accumulate, and validate a complete virtualized conversation DOM."""
        page = await self._select_page()
        policy = _readiness_policy(performance)
        accumulator = _MessageAccumulator()
        started = time.monotonic()
        deadline = started + policy.timeout_seconds
        last_change = started
        stable_observations = 0
        last_signature: tuple[Any, ...] | None = None
        last_state: dict[str, Any] = {}
        poll_seconds = policy.initial_poll_seconds
        LOGGER.info(
            "Conversation DOM observation started (timeout=%.1fs, stabilityWindow=%.1fs)",
            policy.timeout_seconds,
            policy.stability_window_seconds,
        )

        try:
            while time.monotonic() < deadline:
                if cancellation_event.is_set():
                    raise InterruptedError("Conversation loading cancelled.")
                state = await self._observe_conversation(page, scroll_up=False)
                last_state = state
                if bool(state.get("accessDenied")):
                    raise ConversationUnavailableError(
                        "ChatGPT reports that the selected conversation is unavailable or access is denied."
                    )

                accumulator_changed = accumulator.merge(state.get("messages", []))
                signature = _observation_signature(state, accumulator)
                now = time.monotonic()
                if accumulator_changed or signature != last_signature:
                    last_change = now
                    stable_observations = 0
                    poll_seconds = policy.initial_poll_seconds
                    if last_signature is not None:
                        LOGGER.debug(
                            "Conversation changed: messages=%s revision=%s height=%s scrollTop=%s",
                            accumulator.count,
                            state.get("mutationRevision", 0),
                            state.get("scrollHeight", 0),
                            state.get("beforeScrollTop", 0),
                        )
                else:
                    stable_observations += 1
                    poll_seconds = min(policy.maximum_poll_seconds, poll_seconds * 1.35)
                last_signature = signature

                ready_flags = {
                    "document": bool(state.get("documentReady")),
                    "react": bool(state.get("appReady")),
                    "container": bool(state.get("conversationContainer")),
                    "messages": accumulator.count > 0,
                    "top": bool(state.get("atTop")),
                    "streaming": not bool(state.get("streaming")),
                    "continue": not bool(state.get("continueRequired")),
                    "loading": int(state.get("loadingCount", 0)) == 0,
                    "images": (
                        int(state.get("pendingImages", 0)) == 0
                        and accumulator.pending_image_count == 0
                    ),
                }
                stable_for = now - last_change

                if progress_callback is not None:
                    stage, detail = _readiness_progress(
                        state,
                        accumulator.count,
                        accumulator.pending_image_count,
                        stable_for,
                        policy,
                    )
                    elapsed_ratio = min(1.0, (now - started) / max(policy.timeout_seconds, 1.0))
                    activity_ratio = min(1.0, stable_for / max(policy.stability_window_seconds, 0.1))
                    percentage = min(98.0, 5.0 + elapsed_ratio * 30.0 + activity_ratio * 60.0)
                    progress_callback(stage, percentage, detail, accumulator.count, accumulator.count)

                if not bool(state.get("atTop")):
                    window_settled = (
                        bool(state.get("windowReadyToScroll"))
                        and accumulator.pending_image_count == 0
                        and int(state.get("mutationIdleMs", 0)) >= 250
                        and stable_observations >= 1
                    )
                    if window_settled:
                        scroll_state = await self._observe_conversation(page, scroll_up=True)
                        accumulator.merge(scroll_state.get("messages", []))
                        before = float(scroll_state.get("beforeScrollTop", 0.0))
                        after = float(scroll_state.get("afterScrollTop", before))
                        LOGGER.debug(
                            "Deep-scan window committed and scroll requested: before=%s after=%s messages=%s",
                            before,
                            after,
                            accumulator.count,
                        )
                        last_signature = None
                        stable_observations = 0
                        last_change = time.monotonic()
                        poll_seconds = policy.initial_poll_seconds
                    await asyncio.sleep(poll_seconds)
                    continue

                is_ready = (
                    all(ready_flags.values())
                    and stable_for >= policy.stability_window_seconds
                    and stable_observations >= policy.minimum_stable_observations
                )
                if is_ready:
                    final_state = await self._observe_conversation(page, scroll_up=False)
                    final_changed = accumulator.merge(final_state.get("messages", []))
                    final_signature = _observation_signature(final_state, accumulator)
                    final_ready = (
                        not bool(final_state.get("streaming"))
                        and not bool(final_state.get("continueRequired"))
                        and int(final_state.get("loadingCount", 0)) == 0
                        and int(final_state.get("pendingImages", 0)) == 0
                        and accumulator.pending_image_count == 0
                        and bool(final_state.get("atTop"))
                    )
                    if not final_changed and final_signature == signature and final_ready:
                        last_state = final_state
                        break
                    last_signature = final_signature
                    last_change = time.monotonic()
                    stable_observations = 0
                    continue

                await asyncio.sleep(poll_seconds)
            else:
                raise ConversationReadinessError(
                    _readiness_timeout_message(
                        last_state, accumulator.count, accumulator.pending_image_count, policy
                    )
                )

            title = str(last_state.get("title") or "").strip()
            if title.casefold() in {"chatgpt", "new chat"}:
                title = ""
            title = title or await self._page_title(page)
            head_html = await page.locator("head").inner_html()
            snapshot_html = _build_snapshot_html(head_html, accumulator.html_fragments(), title)
            browser_version = await _browser_version(page)
            estimated_size = len(snapshot_html.encode("utf-8"))
            asset_counts = accumulator.asset_counts
            if accumulator.fallback_count:
                LOGGER.warning(
                    "%s message(s) lacked stable ChatGPT identifiers; deterministic content fallbacks were used",
                    accumulator.fallback_count,
                )
            LOGGER.info(
                "Conversation stabilized and deep-scanned: messages=%s size=%s bytes",
                accumulator.count,
                estimated_size,
            )
            if progress_callback is not None:
                progress_callback(
                    "Conversation ready",
                    100.0,
                    f"{accumulator.count} messages validated",
                    accumulator.count,
                    accumulator.count,
                )
            return {
                "html": snapshot_html,
                "url": page.url,
                "title": title,
                "messageCount": accumulator.count,
                "messageKeys": list(accumulator.keys),
                "assetCounts": asset_counts,
                "browserName": "Google Chrome",
                "browserVersion": browser_version,
                "browserProfile": self._profile_directory,
                "chatgptModel": last_state.get("model"),
                "chatgptWorkspace": last_state.get("workspace"),
                "estimatedSize": estimated_size,
                "readiness": {
                    "documentReady": bool(last_state.get("documentReady")),
                    "reactReady": bool(last_state.get("appReady")),
                    "conversationContainer": bool(last_state.get("conversationContainer")),
                    "messageCount": accumulator.count,
                    "mutationRevision": int(last_state.get("mutationRevision", 0)),
                    "scrollHeight": int(last_state.get("scrollHeight", 0)),
                    "streamingComplete": not bool(last_state.get("streaming")),
                    "lazyLoadingComplete": bool(last_state.get("atTop")),
                    "imagesReady": (
                        int(last_state.get("pendingImages", 0)) == 0
                        and accumulator.pending_image_count == 0
                    ),
                    "accumulatedPendingImages": accumulator.pending_image_count,
                    "stabilityWindowSeconds": policy.stability_window_seconds,
                },
            }
        finally:
            try:
                await page.evaluate(_CLEANUP_OBSERVER_SCRIPT)
            except PlaywrightError:
                LOGGER.debug("Unable to clean up DOM observer because the page is unavailable", exc_info=True)

    async def _observe_conversation(self, page: Page, *, scroll_up: bool) -> dict[str, Any]:
        payload = {
            "messageSelector": MESSAGE_SELECTOR,
            "primaryMessageSelector": PRIMARY_MESSAGE_SELECTOR,
            "fallbackMessageSelector": FALLBACK_MESSAGE_SELECTOR,
            "applicationRootSelector": APPLICATION_ROOT_SELECTOR,
            "conversationContainerSelector": CONVERSATION_CONTAINER_SELECTOR,
            "loadingSelector": LOADING_SELECTOR,
            "streamingSelector": STREAMING_SELECTOR,
            "modelSelectors": list(MODEL_SELECTORS),
            "workspaceSelectors": list(WORKSPACE_SELECTORS),
            "scrollUp": scroll_up,
        }
        value = await page.evaluate(_OBSERVATION_SCRIPT, payload)
        if not isinstance(value, dict):
            raise ConversationReadinessError("ChatGPT DOM observation returned an invalid readiness snapshot.")
        return value

    @retry(
        retry=retry_if_exception(_is_retryable_download_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        reraise=True,
    )
    async def download_resource(self, source_url: str) -> dict[str, Any]:
        """Download an authenticated HTTP, data, blob, or ChatGPT UI attachment."""
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
                "suggestedFilename": _filename_from_source(source_url) or "asset",
            }

        parsed = urlparse(source_url)
        if parsed.scheme in {"sandbox", "contextvault-chatgpt-attachment"}:
            page = await self._select_page()
            return await self._download_attachment_via_ui(page, source_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"Unsupported resource URL scheme: {source_url}")

        context = self._require_context()
        page = await self._select_page()
        response = await context.request.get(
            source_url,
            timeout=300_000,
            headers={"referer": page.url, "accept": "*/*"},
        )
        if not response.ok:
            if response.status in {401, 403, 404, 410}:
                LOGGER.info(
                    "Authenticated request returned HTTP %s; attempting the matching ChatGPT download control",
                    response.status,
                )
                return await self._download_attachment_via_ui(page, source_url)
            raise RuntimeError(f"Resource download failed with HTTP {response.status}: {source_url}")
        headers = response.headers
        content_type = headers.get("content-type", "").split(";", 1)[0].strip()
        filename = (
            _filename_from_headers(headers.get("content-disposition", ""))
            or _filename_from_source(source_url)
            or "asset"
        )
        return {
            "content": await response.body(),
            "contentType": content_type,
            "suggestedFilename": sanitize_filename(filename),
        }

    async def _download_attachment_via_ui(self, page: Page, source_url: str) -> dict[str, Any]:
        """Locate a virtualized ChatGPT file control and capture its browser download."""
        descriptor = _attachment_locator(source_url)
        token = f"cv-download-{uuid5(NAMESPACE_URL, source_url).hex}"
        deadline = time.monotonic() + 180.0
        reset = True
        found = False
        bottom_rounds = 0
        while time.monotonic() < deadline:
            state = await page.evaluate(
                _FIND_AND_SCROLL_ATTACHMENT_SCRIPT,
                {
                    "source": descriptor["source"],
                    "filename": descriptor["filename"],
                    "fileId": descriptor["fileId"],
                    "messageId": descriptor["messageId"],
                    "token": token,
                    "reset": reset,
                },
            )
            reset = False
            if isinstance(state, dict) and bool(state.get("found")):
                found = True
                break
            if isinstance(state, dict) and bool(state.get("atBottom")):
                bottom_rounds += 1
                if bottom_rounds >= 3:
                    break
            else:
                bottom_rounds = 0
            await asyncio.sleep(0.35)
        if not found:
            raise RuntimeError(
                "ChatGPT attachment control could not be found after scanning the virtualized conversation: "
                f"{descriptor['filename'] or source_url}"
            )

        locator = page.locator(f'[data-contextvault-download-token="{token}"]').first
        try:
            try:
                await locator.scroll_into_view_if_needed(timeout=15_000)
                async with page.expect_download(timeout=60_000) as download_info:
                    await locator.click(timeout=30_000)
                download = await download_info.value
            except PlaywrightTimeoutError as error:
                raise RuntimeError(
                    "ChatGPT did not start the selected attachment download within the allowed wait period: "
                    f"{descriptor['filename'] or source_url}"
                ) from error

            suggested = sanitize_filename(
                download.suggested_filename
                or descriptor["filename"]
                or _filename_from_source(source_url)
                or "attachment"
            )
            with tempfile.TemporaryDirectory(prefix="contextvault-download-") as directory:
                target = Path(directory) / suggested
                await download.save_as(str(target))
                content = target.read_bytes()
            return {
                "content": content,
                "contentType": mimetypes.guess_type(suggested)[0] or "application/octet-stream",
                "suggestedFilename": suggested,
            }
        finally:
            try:
                await page.evaluate(
                    "token => document.querySelectorAll('[data-contextvault-download-token]').forEach(element => { if (element.getAttribute('data-contextvault-download-token') === token) element.removeAttribute('data-contextvault-download-token'); })",
                    token,
                )
            except PlaywrightError:
                LOGGER.debug("Unable to remove temporary attachment locator token", exc_info=True)

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


def _readiness_policy(performance: PerformanceSettings) -> _ReadinessPolicy:
    timeout_seconds = {"Low": 180.0, "Balanced": 900.0, "High": 1800.0}[performance.memory_mode]
    stability_window_seconds = {"Fast": 1.5, "Normal": 3.0, "Safe": 5.0, "Auto": 3.0}[
        performance.delay_mode
    ]
    maximum_poll_seconds = {"Fast": 0.6, "Normal": 1.0, "Safe": 1.5, "Auto": 1.0}[
        performance.delay_mode
    ]
    return _ReadinessPolicy(
        timeout_seconds=timeout_seconds,
        stability_window_seconds=stability_window_seconds,
        minimum_stable_observations=3,
        initial_poll_seconds=0.1,
        maximum_poll_seconds=maximum_poll_seconds,
    )


def _observation_signature(
    state: dict[str, Any],
    accumulator: _MessageAccumulator,
) -> tuple[Any, ...]:
    """Return the relevant readiness state used to restart stabilization."""
    return (
        accumulator.count,
        accumulator.pending_image_count,
        int(state.get("mutationRevision", 0)),
        int(state.get("beforeScrollTop", 0)),
        int(state.get("scrollHeight", 0)),
        int(state.get("imageCount", 0)),
        int(state.get("attachmentCount", 0)),
        int(state.get("codeBlockCount", 0)),
        int(state.get("tableCount", 0)),
        bool(state.get("streaming")),
        bool(state.get("continueRequired")),
        int(state.get("loadingCount", 0)),
        int(state.get("pendingImages", 0)),
    )


def _readiness_progress(
    state: dict[str, Any],
    accumulated_count: int,
    accumulated_pending_images: int,
    stable_for: float,
    policy: _ReadinessPolicy,
) -> tuple[str, str]:
    if not bool(state.get("documentReady")):
        return "Waiting for browser", "Document is still loading"
    if not bool(state.get("appReady")):
        return "Waiting for ChatGPT", "React application is still rendering"
    if not bool(state.get("conversationContainer")):
        return "Detecting conversation", "Conversation container not available yet"
    if bool(state.get("continueRequired")):
        return "Continue response required", "Use the ChatGPT button to finish the response"
    if bool(state.get("streaming")):
        return "Waiting for response", "ChatGPT is still generating content"
    if accumulated_count == 0:
        return "Waiting for messages", "No messages rendered yet; observation continues"
    if int(state.get("pendingImages", 0)) or accumulated_pending_images:
        return (
            "Waiting for images",
            f"{max(int(state.get('pendingImages', 0)), accumulated_pending_images)} image(s) still rendering",
        )
    if int(state.get("loadingCount", 0)):
        return "Waiting for ChatGPT", "Loading indicators are still active"
    if not bool(state.get("atTop")):
        return "Loading older messages", f"{accumulated_count} messages accumulated"
    return (
        "Conversation stabilizing",
        f"{accumulated_count} messages; stable {stable_for:.1f}/{policy.stability_window_seconds:.1f}s",
    )


def _readiness_timeout_message(
    state: dict[str, Any],
    accumulated_count: int,
    accumulated_pending_images: int,
    policy: _ReadinessPolicy,
) -> str:
    return (
        "Conversation readiness could not be confirmed before the adaptive timeout. "
        f"Observed {accumulated_count} message(s); documentReady={bool(state.get('documentReady'))}, "
        f"reactReady={bool(state.get('appReady'))}, container={bool(state.get('conversationContainer'))}, "
        f"atTop={bool(state.get('atTop'))}, streaming={bool(state.get('streaming'))}, "
        f"continueRequired={bool(state.get('continueRequired'))}, "
        f"pendingImages={int(state.get('pendingImages', 0))}, "
        f"accumulatedPendingImages={accumulated_pending_images}. "
        f"The {policy.timeout_seconds:.0f}-second readiness policy was exhausted without reporting a partial export."
    )


def _merge_order(existing: list[str], incoming: list[str]) -> list[str]:
    """Merge one ordered virtualized window into an existing global order."""
    if not existing:
        return list(incoming)
    result = list(existing)
    if not any(key in result for key in incoming):
        return [*incoming, *[key for key in result if key not in incoming]]

    pending: list[str] = []
    last_anchor: str | None = None
    for key in incoming:
        if key in result:
            if pending:
                insertion_index = result.index(key)
                for new_key in pending:
                    if new_key not in result:
                        result.insert(insertion_index, new_key)
                        insertion_index += 1
                pending.clear()
            last_anchor = key
        elif key not in pending:
            pending.append(key)
    if pending:
        insertion_index = result.index(last_anchor) + 1 if last_anchor in result else 0
        for new_key in pending:
            if new_key not in result:
                result.insert(insertion_index, new_key)
                insertion_index += 1
    return result


def _build_snapshot_html(head_html: str, message_html: list[str], title: str) -> str:
    safe_title = html_module.escape(title, quote=False)
    return (
        "<!doctype html>\n<html>\n<head>\n"
        f"<title>{safe_title}</title>\n{head_html}\n"
        "</head>\n<body>\n<main data-contextvault-snapshot=\"true\">\n"
        + "\n".join(message_html)
        + "\n</main>\n</body>\n</html>\n"
    )


async def _browser_version(page: Page) -> str:
    value = await page.evaluate(
        r"""
        () => {
            const brands = navigator.userAgentData?.brands || [];
            const chrome = brands.find(item => /Google Chrome/i.test(item.brand));
            if (chrome?.version) return chrome.version;
            const match = navigator.userAgent.match(/(?:Chrome|Chromium)\/([0-9.]+)/);
            return match ? match[1] : 'unavailable';
        }
        """
    )
    text = str(value or "unavailable").strip()
    return text or "unavailable"


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
        LOGGER.debug("Unable to compare paths with os.path.samefile: %s, %s", left, right, exc_info=True)
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def default_chrome_user_data_dir() -> Path:
    """Return the conventional regular Chrome user-data directory for detection only."""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            raise BrowserNotReadyError(
                "LOCALAPPDATA is unavailable; select a custom Chrome user-data folder manually."
            )
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


def _attachment_locator(source_url: str) -> dict[str, str]:
    parsed = urlparse(source_url)
    query = parse_qs(parsed.query)
    return {
        "source": source_url if parsed.scheme != "contextvault-chatgpt-attachment" else "",
        "filename": unquote((query.get("filename") or [""])[0]) or _filename_from_source(source_url),
        "fileId": unquote((query.get("fileId") or [""])[0]),
        "messageId": unquote((query.get("messageId") or [""])[0]),
    }


def _filename_from_source(source_url: str) -> str:
    parsed = urlparse(source_url)
    query = parse_qs(parsed.query)
    query_name = (query.get("filename") or query.get("file_name") or [""])[0]
    return unquote(query_name or Path(parsed.path).name).strip()


def _filename_from_headers(content_disposition: str) -> str:
    match = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", content_disposition, re.IGNORECASE)
    return unquote(match.group(1).strip()) if match else ""
