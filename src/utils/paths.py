"""Runtime and project path resolution helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from src.config.constants import (
    DEFAULT_DATA_DIRECTORY_NAME,
    DEFAULT_EXPORT_DIRECTORY_NAME,
    DEFAULT_LOG_DIRECTORY_NAME,
    PROJECT_ROOT_MARKERS,
)


def application_root() -> Path:
    """Return the portable application root or source repository root."""
    try:
        compiled_root = Path(__compiled__.containing_dir).resolve()  # type: ignore[name-defined]
    except NameError:
        compiled_root = None
    if compiled_root is not None:
        return compiled_root
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    current = Path(__file__).resolve()
    for parent in current.parents:
        if all((parent / marker).exists() for marker in PROJECT_ROOT_MARKERS):
            return parent
    return current.parents[2]


def data_directory() -> Path:
    """Return and create the writable application data directory."""
    path = application_root() / DEFAULT_DATA_DIRECTORY_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_directory() -> Path:
    """Return and create the application log directory."""
    path = application_root() / DEFAULT_LOG_DIRECTORY_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_export_directory() -> Path:
    """Return and create the default archive output directory."""
    path = application_root() / DEFAULT_EXPORT_DIRECTORY_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def asset_path(relative_path: str) -> Path:
    """Resolve an asset path from source or portable runtime layouts."""
    root = application_root()
    direct = root / "assets" / relative_path
    if direct.exists():
        return direct
    runtime_asset = root / "runtime" / "assets" / relative_path
    return runtime_asset


def configuration_path(relative_path: str) -> Path:
    """Resolve a shipped configuration path."""
    root = application_root()
    direct = root / "config" / relative_path
    if direct.exists():
        return direct
    return root / "runtime" / "config" / relative_path
