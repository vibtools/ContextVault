"""Core business logic package with lazy public exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "ArchiveBuilder": ("src.core.archive_builder", "ArchiveBuilder"),
    "ArchiveValidator": ("src.core.archive_validator", "ArchiveValidator"),
    "ExportPipeline": ("src.core.export_pipeline", "ExportPipeline"),
    "TaskManager": ("src.core.task_manager", "TaskManager"),
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
