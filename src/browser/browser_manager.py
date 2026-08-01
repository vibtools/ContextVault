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
from typing import Any, Literal
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
    MESSAGE_ID_SELECTOR,
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
ResourceKind = Literal["image", "attachment"]
MessageCheckpointCallback = Callable[
    [list[dict[str, Any]], tuple[str, ...], set[str]],
    dict[str, Any],
]


_OBSERVATION_SCRIPT = r"""
async ({
    messageSelector,
    primaryMessageSelector,
    fallbackMessageSelector,
    messageIdSelector,
    applicationRootSelector,
    conversationContainerSelector,
    loadingSelector,
    streamingSelector,
    modelSelectors,
    workspaceSelectors,
    scrollUp,
    forceScroll
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
            observer: null,
            scroller: null
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
        const selectors = [
            fallbackMessageSelector,
            messageIdSelector,
            primaryMessageSelector,
            'main article'
        ].filter(Boolean);
        const candidates = Array.from(
            document.querySelectorAll(selectors.join(', '))
        ).filter(node => root.contains(node));
        const candidateSet = new Set(candidates);
        return candidates.filter(node => {
            let parent = node.parentElement;
            while (parent && parent !== root.parentElement) {
                if (candidateSet.has(parent)) return false;
                if (parent === root) break;
                parent = parent.parentElement;
            }
            return true;
        });
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
    const documentScroller = document.scrollingElement || document.documentElement;
    const candidates = [];
    const seenCandidates = new Set();

    const addCandidate = candidate => {
        if (!(candidate instanceof Element) || seenCandidates.has(candidate)) return;
        seenCandidates.add(candidate);
        const style = getComputedStyle(candidate);
        const scrollRange = Number(candidate.scrollHeight || 0) - Number(candidate.clientHeight || 0);
        const scrollable = candidate === documentScroller
            || (scrollRange > 50 && /(auto|scroll|overlay)/.test(style.overflowY));
        if (scrollable) candidates.push(candidate);
    };

    const addScrollableAncestors = start => {
        let candidate = start instanceof Element ? start : null;
        while (candidate) {
            addCandidate(candidate);
            if (candidate === document.documentElement) break;
            candidate = candidate.parentElement;
        }
    };

    addScrollableAncestors(messages[0]?.parentElement || root);
    addScrollableAncestors(messages[messages.length - 1]?.parentElement || root);
    addScrollableAncestors(root);
    addCandidate(documentScroller);

    const candidateScore = candidate => {
        const coverage = messages.reduce(
            (count, message) => count + (
                candidate === documentScroller || candidate.contains(message) ? 1 : 0
            ),
            0
        );
        const scrollTop = Math.max(0, Number(candidate.scrollTop || 0));
        const scrollRange = Math.max(
            0,
            Number(candidate.scrollHeight || 0) - Number(candidate.clientHeight || 0)
        );
        const activeBonus = scrollTop > 1 ? 10_000_000_000 : 0;
        const nestedBonus = candidate === documentScroller ? 0 : 1_000_000_000;
        const cachedBonus = candidate === observation.scroller ? 1_000_000 : 0;
        return (
            coverage * 100_000_000_000
            + activeBonus
            + nestedBonus
            + cachedBonus
            + Math.min(scrollRange, 999_999)
        );
    };

    let scroller = candidates.sort(
        (left, right) => candidateScore(right) - candidateScore(left)
    )[0];
    scroller = scroller || documentScroller;
    observation.scroller = scroller;

    const beforeScrollTop = Number(scroller.scrollTop || 0);
    const scrollHeight = Number(scroller.scrollHeight || document.documentElement.scrollHeight || 0);
    const clientHeight = Number(scroller.clientHeight || window.innerHeight || 0);
    const scrollRange = Math.max(0, scrollHeight - clientHeight);
    const scrollerRect = scroller.getBoundingClientRect
        ? scroller.getBoundingClientRect()
        : {top: 0};
    const scrollerIdentity = [
        (scroller.tagName || 'document').toLowerCase(),
        scroller.id ? `#${scroller.id}` : '',
        scroller.getAttribute?.('role') ? `[role=${scroller.getAttribute('role')}]` : '',
        scroller.getAttribute?.('data-testid')
            ? `[data-testid=${scroller.getAttribute('data-testid')}]`
            : ''
    ].filter(Boolean).join('');

    const isElementVisible = element => {
        if (!(element instanceof Element) || !element.isConnected) return false;
        const style = getComputedStyle(element);
        if (
            style.display === 'none'
            || style.visibility === 'hidden'
            || Number.parseFloat(style.opacity || '1') === 0
        ) {
            return false;
        }
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    };

    const isImagePending = image => {
        const source = image.currentSrc || image.src || image.getAttribute('data-src') || '';
        if (!source || source.startsWith('data:image/svg')) return false;
        // A completed image with naturalWidth=0 is terminally broken, not still loading.
        // Asset download later remains the authoritative byte-integrity check.
        return !image.complete;
    };
    const loadingElements = Array.from(document.querySelectorAll(loadingSelector))
        .filter(isElementVisible);
    const isImageLoadingIndicator = element => {
        const message = element.closest(messageSelector);
        if (!message) return false;
        const descriptor = `${element.getAttribute('data-testid') || ''} ${element.getAttribute('aria-label') || ''} ${element.className || ''}`.toLowerCase();
        if (/(image|photo|media|thumbnail)/.test(descriptor)) return true;
        let ancestor = element.parentElement;
        let depth = 0;
        while (ancestor && ancestor !== message && depth < 4) {
            if (ancestor.matches('figure, picture, [data-testid*="image" i], [aria-label*="image" i]')) return true;
            if (ancestor.querySelector(':scope > img, :scope > picture')) return true;
            ancestor = ancestor.parentElement;
            depth += 1;
        }
        return false;
    };
    const imageLoadingElements = loadingElements.filter(isImageLoadingIndicator);
    const blockingLoadingElements = loadingElements.filter(element => !isImageLoadingIndicator(element));
    const blockingLoaderDescriptors = blockingLoadingElements.slice(0, 5).map(element => (
        `${element.tagName.toLowerCase()}`
        + `${element.getAttribute('role') ? `[role=${element.getAttribute('role')}]` : ''}`
        + `${element.getAttribute('data-testid') ? `[data-testid=${element.getAttribute('data-testid')}]` : ''}`
        + `${element.getAttribute('aria-label') ? `[aria-label=${element.getAttribute('aria-label').slice(0, 80)}]` : ''}`
    ));
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
        const semanticClone = node.cloneNode(true);
        semanticClone.querySelectorAll(
            '[role="progressbar"], [aria-busy="true"], [data-loading="true"], '
            + '[data-testid*="loading" i], [data-testid*="spinner" i], '
            + '[data-is-streaming="true"], [data-testid="stop-button"]'
        ).forEach(element => element.remove());
        const semanticText = (
            semanticClone.innerText || semanticClone.textContent || ''
        ).trim();
        const markup = node.outerHTML || '';
        const timestamp = (
            node.getAttribute('data-message-timestamp')
            || node.getAttribute('data-timestamp')
            || node.querySelector('[data-message-timestamp]')?.getAttribute('data-message-timestamp')
            || node.querySelector('[data-timestamp]')?.getAttribute('data-timestamp')
            || node.querySelector('time[datetime]')?.getAttribute('datetime')
            || null
        );
        const signature = `${role}:${hashText(text)}:${hashText(markup)}`;
        const semanticImageValues = Array.from(node.querySelectorAll('img')).map(image => [
            image.currentSrc || image.getAttribute('src') || image.getAttribute('data-src') || '',
            image.getAttribute('alt') || ''
        ]);
        const semanticLinkValues = Array.from(node.querySelectorAll(
            'a[href], [data-download-url], [data-file-url], [data-href], [data-url], '
            + '[data-file-id], [data-filename], [data-file-name]'
        )).map(element => [
            element.getAttribute('href') || '',
            element.getAttribute('data-download-url') || '',
            element.getAttribute('data-file-url') || '',
            element.getAttribute('data-href') || '',
            element.getAttribute('data-url') || '',
            element.getAttribute('data-file-id') || '',
            element.getAttribute('data-filename') || '',
            element.getAttribute('data-file-name') || '',
            (element.innerText || element.textContent || '').trim()
        ]);
        const semanticCodeValues = Array.from(node.querySelectorAll('pre code')).map(code => [
            code.className || '',
            code.textContent || ''
        ]);
        const semanticTableValues = Array.from(node.querySelectorAll('table')).map(
            table => table.textContent || ''
        );
        const semanticSignature = hashText(JSON.stringify([
            role,
            semanticText,
            timestamp || '',
            semanticImageValues,
            semanticLinkValues,
            semanticCodeValues,
            semanticTableValues
        ]));
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
            semanticSignature,
            role,
            fallback,
            domIndex: index,
            documentTop,
            html: markup,
            text,
            timestamp,
            capturedAt: new Date().toISOString(),
            imageCount: nodeImages.length,
            pendingImages: nodeImages.filter(isImagePending).length,
            imageLoadingCount: imageLoadingElements.filter(element => node.contains(element)).length,
            attachmentCount: nodeAttachments.length,
            codeBlockCount: node.querySelectorAll('pre code').length,
            tableCount: node.querySelectorAll('table').length
        };
    });

    const visibleText = (root.innerText || root.textContent || '').toLowerCase();
    const buttons = Array.from(root.querySelectorAll('button')).filter(isElementVisible);
    const continueRequired = buttons.some(button => {
        const text = `${button.innerText || ''} ${button.getAttribute('aria-label') || ''}`.toLowerCase();
        return text.includes('continue generating') || text.includes('continue response');
    });
    const stopGenerating = buttons.some(button => {
        const text = `${button.innerText || ''} ${button.getAttribute('aria-label') || ''}`.toLowerCase();
        return text.includes('stop generating');
    });
    const visibleStreamingElements = Array.from(document.querySelectorAll(streamingSelector))
        .filter(isElementVisible);
    const streaming = visibleStreamingElements.length > 0 || stopGenerating;
    const loadingCount = blockingLoadingElements.length;
    const imageLoadingCount = imageLoadingElements.length;
    const imageCount = serializedMessages.reduce((total, item) => total + item.imageCount, 0);
    const pendingImages = serializedMessages.reduce(
        (total, item) => total + Math.max(item.pendingImages, item.imageLoadingCount),
        0
    );
    const attachmentCount = serializedMessages.reduce((total, item) => total + item.attachmentCount, 0);
    const codeBlockCount = serializedMessages.reduce((total, item) => total + item.codeBlockCount, 0);
    const tableCount = serializedMessages.reduce((total, item) => total + item.tableCount, 0);

    let afterScrollTop = beforeScrollTop;
    let scrollStrategy = 'none';
    const baseWindowReadyToScroll = document.readyState !== 'loading'
        && serializedMessages.length > 0
        && !streaming
        && !continueRequired;
    const windowReadyToScroll = baseWindowReadyToScroll && loadingCount === 0;
    const scrollAllowed = windowReadyToScroll || (forceScroll && baseWindowReadyToScroll);
    if (scrollUp && scrollAllowed && beforeScrollTop > 0) {
        const baseStep = Math.max(600, Math.floor(clientHeight * 0.85));
        const step = forceScroll
            ? Math.max(baseStep * 3, Math.floor(clientHeight * 2.25))
            : baseStep;
        const target = Math.max(0, beforeScrollTop - step);
        scroller.scrollTop = target;
        scrollStrategy = forceScroll ? 'recovery-step' : 'step';
        scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));

        if (forceScroll && Number(scroller.scrollTop || 0) >= beforeScrollTop - 1) {
            const anchor = messages[0];
            if (anchor) {
                anchor.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'auto'});
                scroller.scrollTop = Math.max(0, Number(scroller.scrollTop || beforeScrollTop) - step);
                scrollStrategy = 'recovery-anchor';
                scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
                await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            }
        }
        afterScrollTop = Number(scroller.scrollTop || 0);
    } else if (scrollUp && scrollAllowed && beforeScrollTop <= 1) {
        scrollStrategy = 'top-confirmation';
        scroller.dispatchEvent(new Event('scroll', {bubbles: true}));
        await new Promise(resolve => requestAnimationFrame(resolve));
        afterScrollTop = Number(scroller.scrollTop || 0);
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
        afterScrollTop,
        scrollDelta: afterScrollTop - beforeScrollTop,
        scrollStrategy,
        scrollHeight,
        clientHeight,
        scrollRange,
        scrollerIdentity,
        atTop: afterScrollTop <= 1,
        streaming,
        continueRequired,
        loadingCount,
        blockingLoaderDescriptors,
        imageLoadingCount,
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
    empty_state_recovery_seconds: float = 60.0
    image_render_grace_seconds: float = 20.0
    semantic_stability_window_seconds: float = 3.0
    stall_recovery_seconds: float = 45.0
    maximum_stall_reloads: int = 2
    maximum_noop_scrolls: int = 2


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
    def pending_images_by_key(self) -> dict[str, int]:
        return {
            key: count
            for key in self._order
            if (count := self._pending_images_by_key.get(key, 0)) > 0
        }

    def unresolved_pending_image_count(self, accepted_counts: dict[str, int]) -> int:
        return sum(
            max(0, count - max(0, int(accepted_counts.get(key, 0))))
            for key, count in self.pending_images_by_key.items()
        )

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
            pending_images = max(
                0,
                int(item.get("pendingImages", 0)),
                int(item.get("imageLoadingCount", 0)),
            )
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


def _sidebar_conversation_title(item: dict[str, str]) -> str:
    """Return the canonical ChatGPT sidebar title without project UI context."""
    for field_name in ("attributeTitle", "visibleTitle", "ariaLabel"):
        candidate = _strip_sidebar_title_context(item.get(field_name, ""))
        if candidate:
            return candidate
    return ""


def _compact_title_text(value: str) -> str:
    """Collapse UI whitespace while preserving the visible title text."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _strip_sidebar_title_context(value: str) -> str:
    """Remove ChatGPT accessibility context appended after the real chat title."""
    compact = _compact_title_text(value)
    if not compact:
        return ""
    stripped = re.sub(
        r",?\s*(?:chat|conversation)\s+in\s+project\s+.+$",
        "",
        compact,
        flags=re.IGNORECASE,
    ).strip(" ,-")
    return stripped or compact


def _conversation_identity_suffix(conversation_id: str) -> str:
    """Return a stable short identity suitable for fallback display names."""
    compact = re.sub(r"[^A-Za-z0-9]", "", conversation_id)
    if compact:
        return compact[:8]
    return uuid5(NAMESPACE_URL, conversation_id or "conversation").hex[:8]


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
                        visibleTitle: (element.innerText || element.textContent || '').trim(),
                        attributeTitle: (element.getAttribute('title') || '').trim(),
                        ariaLabel: (element.getAttribute('aria-label') || '').trim()
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
                    discovered[url] = {
                        "href": url,
                        "visibleTitle": str(item.get("visibleTitle") or "").strip(),
                        "attributeTitle": str(item.get("attributeTitle") or "").strip(),
                        "ariaLabel": str(item.get("ariaLabel") or "").strip(),
                    }
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
            title = _sidebar_conversation_title(item)
            if not title:
                title = f"Conversation #{_conversation_identity_suffix(conversation_id)}"
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

    async def load_complete_conversation(
        self,
        *,
        performance: PerformanceSettings,
        cancellation_event: threading.Event,
        progress_callback: ProgressCallback | None = None,
        message_checkpoint_callback: MessageCheckpointCallback | None = None,
    ) -> dict[str, Any]:
        """Observe, accumulate, recover, and validate a complete virtualized conversation DOM."""
        page = await self._select_page()
        policy = _readiness_policy(performance)
        accumulator = _MessageAccumulator()
        started = _monotonic()
        last_change = started
        last_progress = started
        last_semantic_change = started
        stable_observations = 0
        last_signature: tuple[Any, ...] | None = None
        last_semantic_signature: tuple[Any, ...] | None = None
        semantic_stable_observations = 0
        last_progress_state: dict[str, int | bool] | None = None
        highest_scroll_height = 0
        last_state: dict[str, Any] = {}
        poll_seconds = policy.initial_poll_seconds
        verified_checkpoint_keys: set[str] = set()
        skipped_checkpoint_keys: set[str] = set()
        checkpoint_failures: dict[str, int] = {}
        checkpoint_reloaded_keys: set[str] = set()
        checkpoint_reloads = 0
        empty_state_started: float | None = None
        empty_state_reloads = 0
        pending_image_signature: tuple[tuple[str, int], ...] | None = None
        pending_image_started: float | None = None
        accepted_pending_images: dict[str, int] = {}
        stalled_image_count = 0
        capture_warnings: list[str] = []
        semantic_fallback_windows: set[tuple[str, ...]] = set()
        scroll_attempts = 0
        forced_scroll_attempts = 0
        consecutive_noop_scrolls = 0
        stall_reloads = 0
        last_scroll_state: dict[str, Any] = {}

        LOGGER.info(
            "Conversation DOM observation started "
            "(stallTimeout=%.1fs, recoveryWindow=%.1fs, semanticWindow=%.1fs, stabilityWindow=%.1fs)",
            policy.timeout_seconds,
            policy.stall_recovery_seconds,
            policy.semantic_stability_window_seconds,
            policy.stability_window_seconds,
        )

        def diagnostics(now: float) -> dict[str, Any]:
            return {
                "stableObservations": stable_observations,
                "semanticStableObservations": semantic_stable_observations,
                "semanticStableSeconds": max(0.0, now - last_semantic_change),
                "scrollAttempts": scroll_attempts,
                "forcedScrollAttempts": forced_scroll_attempts,
                "consecutiveNoopScrolls": consecutive_noop_scrolls,
                "stallReloads": stall_reloads,
                "checkpointReloads": checkpoint_reloads,
                "emptyStateReloads": empty_state_reloads,
                "verifiedCheckpointMessages": len(
                    verified_checkpoint_keys | skipped_checkpoint_keys
                ),
                "lastScrollBefore": last_scroll_state.get("beforeScrollTop"),
                "lastScrollAfter": last_scroll_state.get("afterScrollTop"),
                "lastScrollDelta": last_scroll_state.get("scrollDelta"),
                "lastScrollStrategy": last_scroll_state.get("scrollStrategy"),
                "scrollerIdentity": (
                    last_scroll_state.get("scrollerIdentity")
                    or last_state.get("scrollerIdentity")
                ),
                "scrollRange": (
                    last_scroll_state.get("scrollRange")
                    or last_state.get("scrollRange")
                ),
            }

        async def recover_stalled_window(reason: str, now: float) -> None:
            nonlocal last_change
            nonlocal last_progress
            nonlocal last_semantic_change
            nonlocal stable_observations
            nonlocal last_signature
            nonlocal last_semantic_signature
            nonlocal semantic_stable_observations
            nonlocal last_progress_state
            nonlocal highest_scroll_height
            nonlocal poll_seconds
            nonlocal pending_image_signature
            nonlocal pending_image_started
            nonlocal consecutive_noop_scrolls
            nonlocal stall_reloads

            if stall_reloads >= policy.maximum_stall_reloads:
                raise ConversationReadinessError(
                    _readiness_timeout_message(
                        last_state,
                        accumulator.count,
                        accumulator.pending_image_count,
                        policy,
                        elapsed_seconds=now - started,
                        inactive_seconds=now - last_progress,
                        diagnostics=diagnostics(now),
                        reason=(
                            f"{reason}; all {policy.maximum_stall_reloads} "
                            "bounded non-empty stall reload(s) were already used"
                        ),
                    )
                )

            stall_reloads += 1
            LOGGER.warning(
                "Recovering stalled non-empty conversation window with reload %s/%s: "
                "%s; messages=%s checkpointed=%s atTop=%s scrollTop=%s "
                "scrollHeight=%s loadingCount=%s mutationIdleMs=%s "
                "semanticStable=%.1fs scroller=%s",
                stall_reloads,
                policy.maximum_stall_reloads,
                reason,
                accumulator.count,
                len(verified_checkpoint_keys | skipped_checkpoint_keys),
                bool(last_state.get("atTop")),
                int(last_state.get("beforeScrollTop", 0)),
                int(last_state.get("scrollHeight", 0)),
                int(last_state.get("loadingCount", 0)),
                int(last_state.get("mutationIdleMs", 0)),
                max(0.0, now - last_semantic_change),
                last_state.get("scrollerIdentity") or "unknown",
            )
            await page.reload(wait_until="domcontentloaded")
            reset_at = _monotonic()
            last_signature = None
            last_semantic_signature = None
            semantic_stable_observations = 0
            last_semantic_change = reset_at
            last_progress_state = None
            highest_scroll_height = 0
            stable_observations = 0
            last_change = reset_at
            last_progress = reset_at
            pending_image_signature = None
            pending_image_started = None
            consecutive_noop_scrolls = 0
            poll_seconds = policy.initial_poll_seconds

        try:
            while True:
                if cancellation_event.is_set():
                    raise InterruptedError("Conversation loading cancelled.")

                state = await self._observe_conversation(
                    page,
                    scroll_up=False,
                    force_scroll=False,
                )
                last_state = state
                if bool(state.get("accessDenied")):
                    raise ConversationUnavailableError(
                        "ChatGPT reports that the selected conversation is unavailable or access is denied."
                    )

                observed_messages = [
                    dict(item)
                    for item in state.get("messages", [])
                    if isinstance(item, dict)
                ]
                previous_count = accumulator.count
                previous_keys = accumulator.keys
                accumulator_changed = accumulator.merge(observed_messages)
                message_progress = (
                    accumulator.count > previous_count
                    or accumulator.keys != previous_keys
                )
                signature = _observation_signature(state, accumulator)
                semantic_signature = _window_semantic_signature(observed_messages)
                now = _monotonic()

                if semantic_signature == last_semantic_signature:
                    semantic_stable_observations += 1
                else:
                    semantic_stable_observations = 0
                    last_semantic_change = now
                last_semantic_signature = semantic_signature

                progress_state = _readiness_progress_state(state, accumulator)
                current_scroll_height = int(progress_state["scrollHeight"])
                readiness_progress = _made_readiness_progress(
                    last_progress_state,
                    progress_state,
                )
                meaningful_progress = (
                    message_progress
                    or readiness_progress
                    or current_scroll_height > highest_scroll_height
                )
                if meaningful_progress:
                    last_progress = now
                    if (
                        message_progress
                        or (
                            last_progress_state is not None
                            and int(progress_state["scrollTop"])
                            < int(last_progress_state["scrollTop"]) - 1
                        )
                    ):
                        consecutive_noop_scrolls = 0
                highest_scroll_height = max(
                    highest_scroll_height,
                    current_scroll_height,
                )
                last_progress_state = progress_state

                current_pending_images = {
                    str(item.get("key") or "").strip(): max(
                        0,
                        int(item.get("pendingImages", 0)),
                        int(item.get("imageLoadingCount", 0)),
                    )
                    for item in observed_messages
                    if str(item.get("key") or "").strip()
                    and max(
                        int(item.get("pendingImages", 0)),
                        int(item.get("imageLoadingCount", 0)),
                    ) > 0
                }
                unresolved_current_pending = {
                    key: max(
                        0,
                        count - max(0, int(accepted_pending_images.get(key, 0))),
                    )
                    for key, count in current_pending_images.items()
                }
                unresolved_current_pending = {
                    key: count
                    for key, count in unresolved_current_pending.items()
                    if count > 0
                }
                current_pending_signature = tuple(
                    sorted(unresolved_current_pending.items())
                )
                if current_pending_signature:
                    if current_pending_signature != pending_image_signature:
                        pending_image_signature = current_pending_signature
                        pending_image_started = now
                        LOGGER.info(
                            "Waiting up to %.1fs for %s currently visible image(s) to finish rendering",
                            policy.image_render_grace_seconds,
                            sum(unresolved_current_pending.values()),
                        )
                    elif (
                        pending_image_started is not None
                        and now - pending_image_started
                        >= policy.image_render_grace_seconds
                    ):
                        newly_accepted = 0
                        accepted_keys: list[str] = []
                        for key, unresolved_count in unresolved_current_pending.items():
                            accepted_pending_images[key] = (
                                max(
                                    0,
                                    int(accepted_pending_images.get(key, 0)),
                                )
                                + unresolved_count
                            )
                            newly_accepted += unresolved_count
                            accepted_keys.append(key)
                        if newly_accepted:
                            stalled_image_count += newly_accepted
                            warning = (
                                f"{newly_accepted} image(s) in {len(accepted_keys)} message(s) "
                                f"did not finish browser rendering within "
                                f"{policy.image_render_grace_seconds:.1f}s. "
                                "ContextVault continued the deep scan because the message markup "
                                "and available image source attributes were checkpointed; archive "
                                "asset download and validation remain authoritative."
                            )
                            capture_warnings.append(warning)
                            LOGGER.warning(warning)
                            last_progress = now
                        unresolved_current_pending = {}
                        pending_image_signature = None
                        pending_image_started = None
                else:
                    pending_image_signature = None
                    pending_image_started = None

                unresolved_accumulated_pending = (
                    accumulator.unresolved_pending_image_count(
                        accepted_pending_images
                    )
                )
                progress_state_for_display = dict(state)
                progress_state_for_display["pendingImages"] = sum(
                    unresolved_current_pending.values()
                )

                empty_idle_state = (
                    accumulator.count == 0
                    and bool(state.get("documentReady"))
                    and bool(state.get("appReady"))
                    and bool(state.get("conversationContainer"))
                    and not bool(state.get("streaming"))
                    and not bool(state.get("continueRequired"))
                    and int(state.get("loadingCount", 0)) == 0
                )
                if empty_idle_state:
                    if empty_state_started is None:
                        empty_state_started = now
                    elif (
                        now - empty_state_started
                        >= policy.empty_state_recovery_seconds
                    ):
                        if empty_state_reloads == 0:
                            empty_state_reloads = 1
                            LOGGER.warning(
                                "Conversation DOM remained idle with zero messages for %.1fs; "
                                "reloading once before declaring the conversation unavailable",
                                now - empty_state_started,
                            )
                            await page.reload(wait_until="domcontentloaded")
                            reset_at = _monotonic()
                            last_signature = None
                            last_semantic_signature = None
                            semantic_stable_observations = 0
                            last_semantic_change = reset_at
                            last_progress_state = None
                            highest_scroll_height = 0
                            stable_observations = 0
                            last_change = reset_at
                            last_progress = reset_at
                            empty_state_started = None
                            pending_image_signature = None
                            pending_image_started = None
                            poll_seconds = policy.initial_poll_seconds
                            continue
                        raise ConversationReadinessError(
                            "Conversation rendered an idle, empty message container after one "
                            "automatic recovery reload. Reopen the conversation in ChatGPT and "
                            "confirm that its messages are visible before retrying the export."
                        )
                else:
                    empty_state_started = None

                if accumulator_changed or signature != last_signature:
                    last_change = now
                    stable_observations = 0
                    poll_seconds = policy.initial_poll_seconds
                    if last_signature is not None:
                        LOGGER.debug(
                            "Conversation changed: messages=%s revision=%s height=%s "
                            "scrollTop=%s mutationIdleMs=%s semanticStable=%.1fs",
                            accumulator.count,
                            state.get("mutationRevision", 0),
                            state.get("scrollHeight", 0),
                            state.get("beforeScrollTop", 0),
                            state.get("mutationIdleMs", 0),
                            max(0.0, now - last_semantic_change),
                        )
                else:
                    stable_observations += 1
                    poll_seconds = min(
                        policy.maximum_poll_seconds,
                        poll_seconds * 1.35,
                    )
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
                        not unresolved_current_pending
                        and unresolved_accumulated_pending == 0
                    ),
                }
                stable_for = now - last_change
                semantic_stable_for = now - last_semantic_change

                if progress_callback is not None:
                    stage, detail = _readiness_progress(
                        progress_state_for_display,
                        accumulator.count,
                        unresolved_accumulated_pending,
                        stable_for,
                        policy,
                    )
                    progress_ratio = min(
                        1.0,
                        accumulator.count / max(accumulator.count + 20, 1),
                    )
                    activity_ratio = min(
                        1.0,
                        max(stable_for, semantic_stable_for)
                        / max(policy.stability_window_seconds, 0.1),
                    )
                    readiness_ratio = sum(ready_flags.values()) / len(ready_flags)
                    percentage = min(
                        98.0,
                        5.0
                        + readiness_ratio * 45.0
                        + progress_ratio * 25.0
                        + activity_ratio * 20.0,
                    )
                    progress_callback(
                        stage,
                        percentage,
                        detail,
                        accumulator.count,
                        accumulator.count,
                    )

                mutation_stability_confirmed = (
                    int(state.get("mutationIdleMs", 0)) >= 250
                    and stable_observations >= 1
                )
                stalled_image_window = (
                    bool(current_pending_images)
                    and not unresolved_current_pending
                )
                image_stall_semantic_confirmed = (
                    stalled_image_window
                    and semantic_stable_observations >= 1
                )
                general_semantic_stability_confirmed = (
                    semantic_stable_observations
                    >= policy.minimum_stable_observations
                    and semantic_stable_for
                    >= policy.semantic_stability_window_seconds
                )
                semantic_stability_confirmed = (
                    image_stall_semantic_confirmed
                    or general_semantic_stability_confirmed
                )
                semantic_loader_recovery_confirmed = (
                    general_semantic_stability_confirmed
                    and semantic_stable_for >= policy.stall_recovery_seconds
                    and bool(state.get("documentReady"))
                    and bool(state.get("appReady"))
                    and bool(state.get("conversationContainer"))
                    and accumulator.count > 0
                    and not bool(state.get("streaming"))
                    and not bool(state.get("continueRequired"))
                    and not unresolved_current_pending
                    and unresolved_accumulated_pending == 0
                )
                window_settled = (
                    (
                        bool(state.get("windowReadyToScroll"))
                        or semantic_loader_recovery_confirmed
                    )
                    and not unresolved_current_pending
                    and (
                        mutation_stability_confirmed
                        or semantic_stability_confirmed
                    )
                )

                window_items = [
                    dict(item)
                    for item in state.get("messages", [])
                    if isinstance(item, dict)
                ]
                current_window_keys = tuple(
                    str(item.get("key") or "").strip()
                    for item in window_items
                    if str(item.get("key") or "").strip()
                )
                if (
                    window_settled
                    and semantic_stability_confirmed
                    and (
                        not mutation_stability_confirmed
                        or semantic_loader_recovery_confirmed
                    )
                    and current_window_keys not in semantic_fallback_windows
                ):
                    semantic_fallback_windows.add(current_window_keys)
                    LOGGER.warning(
                        "Using semantic window recovery after %.1fs of unchanged "
                        "message content: messages=%s revision=%s "
                        "mutationIdleMs=%s loadingCount=%s "
                        "windowReadyToScroll=%s scroller=%s",
                        semantic_stable_for,
                        len(current_window_keys),
                        state.get("mutationRevision", 0),
                        state.get("mutationIdleMs", 0),
                        state.get("loadingCount", 0),
                        bool(state.get("windowReadyToScroll")),
                        state.get("scrollerIdentity") or "unknown",
                    )

                if window_settled and message_checkpoint_callback is not None:
                    result = _invoke_message_checkpoint(
                        message_checkpoint_callback,
                        window_items,
                        accumulator.keys,
                        set(),
                    )
                    verified_checkpoint_keys.update(result["verifiedKeys"])
                    skipped_checkpoint_keys.difference_update(
                        result["verifiedKeys"]
                    )
                    skipped_checkpoint_keys.update(result["skippedKeys"])
                    verified_checkpoint_keys.difference_update(
                        result["skippedKeys"]
                    )
                    failed = result["failed"]
                    for key in result["verifiedKeys"]:
                        checkpoint_failures.pop(key, None)
                    for key in result["skippedKeys"]:
                        checkpoint_failures.pop(key, None)

                    if failed:
                        exhausted: set[str] = set()
                        recoverable: set[str] = set()
                        for key in failed:
                            attempts = checkpoint_failures.get(key, 0) + 1
                            checkpoint_failures[key] = attempts
                            if attempts > performance.message_retry_count:
                                exhausted.add(key)
                            else:
                                recoverable.add(key)

                        if exhausted:
                            degraded = _invoke_message_checkpoint(
                                message_checkpoint_callback,
                                window_items,
                                accumulator.keys,
                                exhausted,
                            )
                            if degraded["failed"]:
                                raise ConversationReadinessError(
                                    "A message could not be preserved after checkpoint "
                                    "retries were exhausted: "
                                    + _format_checkpoint_failures(
                                        degraded["failed"]
                                    )
                                )
                            verified_checkpoint_keys.update(
                                degraded["verifiedKeys"]
                            )
                            skipped_checkpoint_keys.difference_update(
                                degraded["verifiedKeys"]
                            )
                            skipped_checkpoint_keys.update(
                                degraded["skippedKeys"]
                            )
                            verified_checkpoint_keys.difference_update(
                                degraded["skippedKeys"]
                            )
                            unresolved = exhausted.difference(
                                degraded["verifiedKeys"],
                                degraded["skippedKeys"],
                            )
                            if unresolved:
                                raise ConversationReadinessError(
                                    "Checkpoint degradation did not preserve all "
                                    "exhausted messages: "
                                    + ", ".join(sorted(unresolved))
                                )
                            for key in exhausted:
                                checkpoint_failures.pop(key, None)

                        reload_keys = {
                            key
                            for key in recoverable
                            if key not in checkpoint_reloaded_keys
                        }
                        if reload_keys:
                            checkpoint_reloaded_keys.update(reload_keys)
                            checkpoint_reloads += 1
                            LOGGER.warning(
                                "Reloading ChatGPT once to recover %s failed "
                                "message checkpoint(s): %s",
                                len(reload_keys),
                                ", ".join(sorted(reload_keys)[:5]),
                            )
                            await page.reload(wait_until="domcontentloaded")
                            reset_at = _monotonic()
                            last_signature = None
                            last_semantic_signature = None
                            semantic_stable_observations = 0
                            last_semantic_change = reset_at
                            last_progress_state = None
                            highest_scroll_height = 0
                            stable_observations = 0
                            last_change = reset_at
                            last_progress = reset_at
                            pending_image_signature = None
                            pending_image_started = None
                            consecutive_noop_scrolls = 0
                            poll_seconds = policy.initial_poll_seconds
                            continue

                        if recoverable:
                            last_change = _monotonic()
                            stable_observations = 0
                            poll_seconds = policy.initial_poll_seconds
                            await asyncio.sleep(poll_seconds)
                            continue

                inactive_for = now - last_progress

                if not bool(state.get("atTop")):
                    if window_settled:
                        force_scroll = (
                            consecutive_noop_scrolls > 0
                            or semantic_loader_recovery_confirmed
                        )
                        before_count = accumulator.count
                        before_keys = accumulator.keys
                        scroll_state = await self._observe_conversation(
                            page,
                            scroll_up=True,
                            force_scroll=force_scroll,
                        )
                        last_scroll_state = dict(scroll_state)
                        scroll_attempts += 1
                        if force_scroll:
                            forced_scroll_attempts += 1
                        accumulator.merge(scroll_state.get("messages", []))
                        scroll_message_progress = (
                            accumulator.count > before_count
                            or accumulator.keys != before_keys
                        )
                        before = float(
                            scroll_state.get("beforeScrollTop", 0.0)
                        )
                        after = float(
                            scroll_state.get("afterScrollTop", before)
                        )
                        moved = (
                            scroll_message_progress
                            or after < before - 1
                            or bool(scroll_state.get("atTop"))
                        )
                        LOGGER.info(
                            "Deep-scan scroll requested: strategy=%s force=%s "
                            "before=%s after=%s delta=%s messages=%s "
                            "scroller=%s loadingCount=%s",
                            scroll_state.get("scrollStrategy") or "unknown",
                            force_scroll,
                            before,
                            after,
                            scroll_state.get("scrollDelta"),
                            accumulator.count,
                            scroll_state.get("scrollerIdentity") or "unknown",
                            scroll_state.get("loadingCount", 0),
                        )
                        last_signature = None
                        last_semantic_signature = None
                        semantic_stable_observations = 0
                        stable_observations = 0
                        reset_at = _monotonic()
                        last_semantic_change = reset_at
                        last_change = reset_at
                        last_progress_state = _readiness_progress_state(
                            scroll_state,
                            accumulator,
                        )
                        highest_scroll_height = max(
                            highest_scroll_height,
                            int(last_progress_state["scrollHeight"]),
                        )
                        poll_seconds = policy.initial_poll_seconds

                        if moved:
                            last_progress = reset_at
                            consecutive_noop_scrolls = 0
                        else:
                            consecutive_noop_scrolls += 1
                            LOGGER.warning(
                                "Conversation scroll made no upward progress "
                                "(attempt=%s force=%s noop=%s/%s before=%s "
                                "after=%s scroller=%s range=%s)",
                                scroll_attempts,
                                force_scroll,
                                consecutive_noop_scrolls,
                                policy.maximum_noop_scrolls,
                                before,
                                after,
                                scroll_state.get("scrollerIdentity")
                                or "unknown",
                                scroll_state.get("scrollRange", 0),
                            )
                            if (
                                consecutive_noop_scrolls
                                >= policy.maximum_noop_scrolls
                            ):
                                await recover_stalled_window(
                                    "normal and recovery scroll strategies "
                                    "made no upward progress",
                                    reset_at,
                                )
                                continue
                    elif (
                        accumulator.count > 0
                        and inactive_for
                        >= policy.stall_recovery_seconds
                    ):
                        blockers = state.get("blockingLoaderDescriptors") or []
                        reason = (
                            "the current non-empty DOM window could not become "
                            "safe to checkpoint and scroll"
                        )
                        if blockers:
                            reason += (
                                "; visible blocking loader(s): "
                                + ", ".join(str(item) for item in blockers[:5])
                            )
                        await recover_stalled_window(reason, now)
                        continue

                    if inactive_for >= policy.timeout_seconds:
                        raise ConversationReadinessError(
                            _readiness_timeout_message(
                                last_state,
                                accumulator.count,
                                accumulator.pending_image_count,
                                policy,
                                elapsed_seconds=now - started,
                                inactive_seconds=inactive_for,
                                diagnostics=diagnostics(now),
                            )
                        )
                    await asyncio.sleep(poll_seconds)
                    continue

                readiness_stability_confirmed = (
                    (
                        stable_for >= policy.stability_window_seconds
                        and stable_observations
                        >= policy.minimum_stable_observations
                    )
                    or semantic_stability_confirmed
                )
                is_ready = (
                    all(ready_flags.values())
                    and readiness_stability_confirmed
                    and (
                        message_checkpoint_callback is None
                        or set(accumulator.keys).issubset(
                            verified_checkpoint_keys
                            | skipped_checkpoint_keys
                        )
                    )
                )
                if is_ready:
                    final_state = await self._observe_conversation(
                        page,
                        scroll_up=False,
                        force_scroll=False,
                    )
                    final_messages = [
                        dict(item)
                        for item in final_state.get("messages", [])
                        if isinstance(item, dict)
                    ]
                    final_changed = accumulator.merge(final_messages)
                    final_signature = _observation_signature(
                        final_state,
                        accumulator,
                    )
                    final_semantic_signature = _window_semantic_signature(
                        final_messages
                    )
                    final_pending_images = {
                        str(item.get("key") or "").strip(): max(
                            0,
                            int(item.get("pendingImages", 0)),
                            int(item.get("imageLoadingCount", 0)),
                        )
                        for item in final_messages
                        if str(item.get("key") or "").strip()
                        and max(
                            int(item.get("pendingImages", 0)),
                            int(item.get("imageLoadingCount", 0)),
                        ) > 0
                    }
                    final_unresolved_pending = sum(
                        max(
                            0,
                            count
                            - max(
                                0,
                                int(accepted_pending_images.get(key, 0)),
                            ),
                        )
                        for key, count in final_pending_images.items()
                    )
                    final_ready = (
                        not bool(final_state.get("streaming"))
                        and not bool(final_state.get("continueRequired"))
                        and int(final_state.get("loadingCount", 0)) == 0
                        and final_unresolved_pending == 0
                        and accumulator.unresolved_pending_image_count(
                            accepted_pending_images
                        )
                        == 0
                        and bool(final_state.get("atTop"))
                    )
                    final_observation_stable = (
                        not final_changed
                        and (
                            final_signature == signature
                            or (
                                semantic_stability_confirmed
                                and final_semantic_signature
                                == semantic_signature
                            )
                        )
                    )
                    if final_observation_stable and final_ready:
                        last_state = final_state
                        break
                    last_signature = final_signature
                    last_semantic_signature = final_semantic_signature
                    last_semantic_change = _monotonic()
                    last_change = last_semantic_change
                    stable_observations = 0
                    semantic_stable_observations = 0
                    continue

                if inactive_for >= policy.timeout_seconds:
                    raise ConversationReadinessError(
                        _readiness_timeout_message(
                            last_state,
                            accumulator.count,
                            accumulator.pending_image_count,
                            policy,
                            elapsed_seconds=now - started,
                            inactive_seconds=inactive_for,
                            diagnostics=diagnostics(now),
                        )
                    )

                await asyncio.sleep(poll_seconds)

            title = str(last_state.get("title") or "").strip()
            if title.casefold() in {"chatgpt", "new chat"}:
                title = ""
            title = title or await self._page_title(page)
            head_html = await page.locator("head").inner_html()
            snapshot_html = _build_snapshot_html(
                head_html,
                accumulator.html_fragments(),
                title,
            )
            browser_version = await _browser_version(page)
            estimated_size = len(snapshot_html.encode("utf-8"))
            asset_counts = accumulator.asset_counts
            if accumulator.fallback_count:
                LOGGER.warning(
                    "%s message(s) lacked stable ChatGPT identifiers; "
                    "deterministic content fallbacks were used",
                    accumulator.fallback_count,
                )
            LOGGER.info(
                "Conversation stabilized and deep-scanned: messages=%s "
                "size=%s bytes scrollAttempts=%s forcedScrollAttempts=%s "
                "stallReloads=%s semanticFallbackWindows=%s",
                accumulator.count,
                estimated_size,
                scroll_attempts,
                forced_scroll_attempts,
                stall_reloads,
                len(semantic_fallback_windows),
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
                "captureWarnings": capture_warnings,
                "readiness": {
                    "documentReady": bool(last_state.get("documentReady")),
                    "reactReady": bool(last_state.get("appReady")),
                    "conversationContainer": bool(
                        last_state.get("conversationContainer")
                    ),
                    "messageCount": accumulator.count,
                    "mutationRevision": int(
                        last_state.get("mutationRevision", 0)
                    ),
                    "mutationIdleMs": int(
                        last_state.get("mutationIdleMs", 0)
                    ),
                    "scrollHeight": int(last_state.get("scrollHeight", 0)),
                    "scrollerIdentity": (
                        last_state.get("scrollerIdentity") or "unknown"
                    ),
                    "streamingComplete": not bool(
                        last_state.get("streaming")
                    ),
                    "lazyLoadingComplete": bool(last_state.get("atTop")),
                    "imagesReady": (
                        accumulator.unresolved_pending_image_count(
                            accepted_pending_images
                        )
                        == 0
                    ),
                    "accumulatedPendingImages": (
                        accumulator.pending_image_count
                    ),
                    "unresolvedPendingImages": (
                        accumulator.unresolved_pending_image_count(
                            accepted_pending_images
                        )
                    ),
                    "stalledImageCount": stalled_image_count,
                    "imageRenderGraceSeconds": (
                        policy.image_render_grace_seconds
                    ),
                    "stabilityWindowSeconds": (
                        policy.stability_window_seconds
                    ),
                    "semanticStabilityWindowSeconds": (
                        policy.semantic_stability_window_seconds
                    ),
                    "incrementalVerification": (
                        message_checkpoint_callback is not None
                    ),
                    "checkpointedMessages": len(
                        verified_checkpoint_keys
                        | skipped_checkpoint_keys
                    ),
                    "checkpointReloads": checkpoint_reloads,
                    "emptyStateReloads": empty_state_reloads,
                    "stallReloads": stall_reloads,
                    "scrollAttempts": scroll_attempts,
                    "forcedScrollAttempts": forced_scroll_attempts,
                    "semanticFallbackWindows": len(
                        semantic_fallback_windows
                    ),
                    "messageRetryCount": (
                        performance.message_retry_count
                    ),
                },
            }
        finally:
            try:
                await page.evaluate(_CLEANUP_OBSERVER_SCRIPT)
            except PlaywrightError:
                LOGGER.debug(
                    "Unable to clean up DOM observer because the page is unavailable",
                    exc_info=True,
                )

    async def _observe_conversation(
        self,
        page: Page,
        *,
        scroll_up: bool,
        force_scroll: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "messageSelector": MESSAGE_SELECTOR,
            "primaryMessageSelector": PRIMARY_MESSAGE_SELECTOR,
            "fallbackMessageSelector": FALLBACK_MESSAGE_SELECTOR,
            "messageIdSelector": MESSAGE_ID_SELECTOR,
            "applicationRootSelector": APPLICATION_ROOT_SELECTOR,
            "conversationContainerSelector": CONVERSATION_CONTAINER_SELECTOR,
            "loadingSelector": LOADING_SELECTOR,
            "streamingSelector": STREAMING_SELECTOR,
            "modelSelectors": list(MODEL_SELECTORS),
            "workspaceSelectors": list(WORKSPACE_SELECTORS),
            "scrollUp": scroll_up,
            "forceScroll": force_scroll,
        }
        last_error: BaseException | None = None
        for attempt in range(1, 4):
            try:
                value = await page.evaluate(_OBSERVATION_SCRIPT, payload)
            except (PlaywrightTimeoutError, PlaywrightError) as exc:
                last_error = exc
                if attempt >= 3:
                    raise
                LOGGER.warning(
                    "Transient ChatGPT DOM observation failure; retrying in-place "
                    "without resetting accumulated messages (attempt=%s/3): %s",
                    attempt,
                    exc,
                )
                await asyncio.sleep(min(3.0, 0.5 * (2 ** (attempt - 1))))
                continue
            if not isinstance(value, dict):
                raise ConversationReadinessError(
                    "ChatGPT DOM observation returned an invalid readiness snapshot."
                )
            return value
        if last_error is not None:
            raise last_error
        raise ConversationReadinessError(
            "ChatGPT DOM observation failed without a diagnostic exception."
        )

    @retry(
        retry=retry_if_exception(_is_retryable_download_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=3),
        reraise=True,
    )
    async def download_resource(
        self,
        source_url: str,
        resource_kind: ResourceKind = "attachment",
    ) -> dict[str, Any]:
        """Download one typed resource without routing images through attachment UI recovery."""
        if resource_kind not in {"image", "attachment"}:
            raise ValueError(f"Unsupported resource kind: {resource_kind}")
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
            if resource_kind != "attachment":
                raise RuntimeError(
                    f"Image resource cannot be recovered through the ChatGPT attachment UI: {source_url}"
                )
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
            if resource_kind == "attachment" and response.status in {401, 403, 404, 410}:
                LOGGER.info(
                    "Attachment request returned HTTP %s; attempting the matching ChatGPT download control",
                    response.status,
                )
                return await self._download_attachment_via_ui(page, source_url)
            raise RuntimeError(
                f"{resource_kind.title()} resource download failed with HTTP {response.status}: {source_url}"
            )
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


def _monotonic() -> float:
    """Return the process monotonic clock through a testable local boundary."""
    return time.monotonic()



def _readiness_policy(performance: PerformanceSettings) -> _ReadinessPolicy:
    timeout_seconds = {"Low": 180.0, "Balanced": 900.0, "High": 1800.0}[performance.memory_mode]
    stability_window_seconds = {"Fast": 1.5, "Normal": 3.0, "Safe": 5.0, "Auto": 3.0}[
        performance.delay_mode
    ]
    maximum_poll_seconds = {"Fast": 0.6, "Normal": 1.0, "Safe": 1.5, "Auto": 1.0}[
        performance.delay_mode
    ]
    empty_state_recovery_seconds = {
        "Fast": 30.0,
        "Normal": 60.0,
        "Safe": 90.0,
        "Auto": 60.0,
    }[performance.delay_mode]
    image_render_grace_seconds = {
        "Fast": 8.0,
        "Normal": 20.0,
        "Safe": 45.0,
        "Auto": 20.0,
    }[performance.delay_mode]
    semantic_stability_window_seconds = {
        "Fast": 1.5,
        "Normal": 3.0,
        "Safe": 5.0,
        "Auto": 3.0,
    }[performance.delay_mode]
    stall_recovery_seconds = {
        "Fast": 20.0,
        "Normal": 45.0,
        "Safe": 90.0,
        "Auto": 45.0,
    }[performance.delay_mode]
    return _ReadinessPolicy(
        timeout_seconds=timeout_seconds,
        stability_window_seconds=stability_window_seconds,
        minimum_stable_observations=3,
        initial_poll_seconds=0.1,
        maximum_poll_seconds=maximum_poll_seconds,
        empty_state_recovery_seconds=empty_state_recovery_seconds,
        image_render_grace_seconds=image_render_grace_seconds,
        semantic_stability_window_seconds=semantic_stability_window_seconds,
        stall_recovery_seconds=stall_recovery_seconds,
        maximum_stall_reloads=2,
        maximum_noop_scrolls=2,
    )


def _window_semantic_signature(messages: Iterable[dict[str, Any]]) -> tuple[Any, ...]:
    """Return stable message semantics while ignoring transient image-render DOM churn."""
    return tuple(
        (
            str(item.get("key") or ""),
            str(item.get("semanticSignature") or "")
            or (
                str(item.get("role") or "")
                + "|"
                + str(item.get("text") or "")
                + "|"
                + str(item.get("timestamp") or "")
                + "|"
                + str(max(0, int(item.get("imageCount", 0))))
                + "|"
                + str(max(0, int(item.get("attachmentCount", 0))))
                + "|"
                + str(max(0, int(item.get("codeBlockCount", 0))))
                + "|"
                + str(max(0, int(item.get("tableCount", 0))))
            ),
        )
        for item in messages
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
        int(state.get("imageLoadingCount", 0)),
        int(state.get("pendingImages", 0)),
    )


def _readiness_progress_state(
    state: dict[str, Any],
    accumulator: _MessageAccumulator,
) -> dict[str, int | bool]:
    """Return monotonic/readiness signals used by the no-progress timeout."""
    return {
        "messageCount": accumulator.count,
        "accumulatedPendingImages": accumulator.pending_image_count,
        "documentReady": bool(state.get("documentReady")),
        "appReady": bool(state.get("appReady")),
        "conversationContainer": bool(state.get("conversationContainer")),
        "atTop": bool(state.get("atTop")),
        "scrollTop": int(state.get("beforeScrollTop", 0)),
        "scrollHeight": int(state.get("scrollHeight", 0)),
        "streaming": bool(state.get("streaming")),
        "continueRequired": bool(state.get("continueRequired")),
        "loadingCount": int(state.get("loadingCount", 0)),
        "imageLoadingCount": int(state.get("imageLoadingCount", 0)),
        "pendingImages": int(state.get("pendingImages", 0)),
    }


def _made_readiness_progress(
    previous: dict[str, int | bool] | None,
    current: dict[str, int | bool],
) -> bool:
    """Return whether readiness moved materially toward a complete conversation."""
    if previous is None:
        return True
    if int(current["messageCount"]) > int(previous["messageCount"]):
        return True
    if int(current["scrollTop"]) < int(previous["scrollTop"]) - 1:
        return True
    for flag in ("documentReady", "appReady", "conversationContainer", "atTop"):
        if bool(current[flag]) and not bool(previous[flag]):
            return True
    for flag in ("streaming", "continueRequired"):
        if bool(previous[flag]) and not bool(current[flag]):
            return True
    for count in ("loadingCount", "pendingImages", "accumulatedPendingImages"):
        if int(current[count]) < int(previous[count]):
            return True
    return False


def _invoke_message_checkpoint(
    callback: MessageCheckpointCallback,
    items: list[dict[str, Any]],
    order: tuple[str, ...],
    skip_keys: set[str],
) -> dict[str, Any]:
    """Invoke and validate one plain-data checkpoint callback result."""
    value = callback(items, order, skip_keys)
    if not isinstance(value, dict):
        raise ConversationReadinessError("Message checkpoint callback returned an invalid result.")
    verified = {
        str(key).strip()
        for key in value.get("verifiedKeys", [])
        if str(key).strip()
    }
    skipped = {
        str(key).strip()
        for key in value.get("skippedKeys", [])
        if str(key).strip()
    }
    raw_failed = value.get("failed", {})
    if not isinstance(raw_failed, dict):
        raise ConversationReadinessError("Message checkpoint callback returned invalid failures.")
    failed = {
        str(key).strip(): str(reason or "Checkpoint verification failed.")
        for key, reason in raw_failed.items()
        if str(key).strip()
    }
    expected_keys: list[str] = []
    for index, item in enumerate(items, start=1):
        key = str(item.get("key") or "").strip()
        if not key:
            raise ConversationReadinessError(
                f"Observed checkpoint window item {index} has no stable message key."
            )
        if key in expected_keys:
            raise ConversationReadinessError(
                f"Observed checkpoint window contains duplicate message key: {key}"
            )
        expected_keys.append(key)
    overlap = (verified & skipped) | (verified & set(failed)) | (skipped & set(failed))
    if overlap:
        raise ConversationReadinessError(
            "Message checkpoint callback classified the same key more than once: "
            + ", ".join(sorted(overlap))
        )
    expected = set(expected_keys)
    reported = verified | skipped | set(failed)
    unexpected = reported - expected
    if unexpected:
        raise ConversationReadinessError(
            "Message checkpoint callback reported keys outside the current DOM window: "
            + ", ".join(sorted(unexpected))
        )
    for key in expected - reported:
        failed[key] = "Message checkpoint callback did not report a verification result."
    return {
        "verifiedKeys": verified,
        "skippedKeys": skipped,
        "failed": failed,
    }


def _format_checkpoint_failures(failures: dict[str, str]) -> str:
    return "; ".join(
        f"{key}: {reason}"
        for key, reason in sorted(failures.items())[:5]
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
    *,
    elapsed_seconds: float | None = None,
    inactive_seconds: float | None = None,
    diagnostics: dict[str, Any] | None = None,
    reason: str | None = None,
) -> str:
    elapsed = "" if elapsed_seconds is None else f" elapsed={elapsed_seconds:.1f}s;"
    inactive = (
        ""
        if inactive_seconds is None
        else f" noMeaningfulProgress={inactive_seconds:.1f}s;"
    )
    extra = dict(diagnostics or {})
    diagnostic_text = (
        f" windowReadyToScroll={bool(state.get('windowReadyToScroll'))},"
        f" loadingCount={int(state.get('loadingCount', 0))},"
        f" mutationRevision={int(state.get('mutationRevision', 0))},"
        f" mutationIdleMs={int(state.get('mutationIdleMs', 0))},"
        f" afterScrollTop={int(state.get('afterScrollTop', state.get('beforeScrollTop', 0)))},"
        f" scrollDelta={int(state.get('scrollDelta', 0))},"
        f" scrollStrategy={state.get('scrollStrategy') or extra.get('lastScrollStrategy') or 'none'},"
        f" scroller={state.get('scrollerIdentity') or extra.get('scrollerIdentity') or 'unknown'},"
        f" scrollRange={int(state.get('scrollRange', extra.get('scrollRange') or 0))},"
        f" stableObservations={int(extra.get('stableObservations') or 0)},"
        f" semanticStableObservations={int(extra.get('semanticStableObservations') or 0)},"
        f" semanticStableSeconds={float(extra.get('semanticStableSeconds') or 0.0):.1f},"
        f" scrollAttempts={int(extra.get('scrollAttempts') or 0)},"
        f" forcedScrollAttempts={int(extra.get('forcedScrollAttempts') or 0)},"
        f" consecutiveNoopScrolls={int(extra.get('consecutiveNoopScrolls') or 0)},"
        f" stallReloads={int(extra.get('stallReloads') or 0)},"
        f" checkpointReloads={int(extra.get('checkpointReloads') or 0)},"
        f" emptyStateReloads={int(extra.get('emptyStateReloads') or 0)},"
        f" verifiedCheckpointMessages={int(extra.get('verifiedCheckpointMessages') or 0)}"
    )
    blocking_loaders = state.get("blockingLoaderDescriptors")
    if isinstance(blocking_loaders, list) and blocking_loaders:
        diagnostic_text += (
            ", blockingLoaders="
            + "|".join(str(item) for item in blocking_loaders[:5])
        )
    reason_text = "" if not reason else f" Recovery stopped because {reason}."
    return (
        "Conversation readiness could not be confirmed because the adaptive progress window stalled. "
        f"Observed {accumulated_count} message(s); documentReady={bool(state.get('documentReady'))}, "
        f"reactReady={bool(state.get('appReady'))}, container={bool(state.get('conversationContainer'))}, "
        f"atTop={bool(state.get('atTop'))}, streaming={bool(state.get('streaming'))}, "
        f"continueRequired={bool(state.get('continueRequired'))}, "
        f"pendingImages={int(state.get('pendingImages', 0))}, "
        f"imageLoadingCount={int(state.get('imageLoadingCount', 0))}, "
        f"accumulatedPendingImages={accumulated_pending_images}, "
        f"scrollTop={int(state.get('beforeScrollTop', 0))}, "
        f"scrollHeight={int(state.get('scrollHeight', 0))};{elapsed}{inactive}"
        f"{diagnostic_text}.{reason_text} "
        f"The {policy.timeout_seconds:.0f}-second no-progress policy remains the final safety limit; "
        "no partial export was published."
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
