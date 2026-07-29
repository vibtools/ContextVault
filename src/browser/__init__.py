"""Centralized Playwright browser package with lazy public exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "BrowserManager": ("src.browser.browser_manager", "BrowserManager"),
    "BrowserNotReadyError": ("src.browser.browser_manager", "BrowserNotReadyError"),
    "BrowserSessionWorker": ("src.browser.session_worker", "BrowserSessionWorker"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value
