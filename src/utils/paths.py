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


PORTABLE_RUNTIME_MARKERS = (
    "runtime/config/defaults.json",
    "runtime/assets",
    "runtime/icons",
    "runtime/schemas",
    "runtime/templates",
    "runtime/themes",
)


def portable_runtime_missing_paths(root: Path | None = None) -> tuple[str, ...]:
    """Return missing portable-runtime markers without mutating the filesystem."""
    candidate = (root or application_root()).resolve()
    return tuple(
        relative
        for relative in PORTABLE_RUNTIME_MARKERS
        if not (candidate / relative).exists()
    )


def _is_complete_portable_root(root: Path) -> bool:
    """Return whether *root* contains the minimum immutable runtime payload."""
    return not portable_runtime_missing_paths(root)


def application_root() -> Path:
    """Return the portable application root or source repository root."""
    try:
        compiled_root = Path(__compiled__.containing_dir).resolve()  # type: ignore[name-defined]
    except NameError:
        compiled_root = None

    if compiled_root is not None:
        executable_root = Path(sys.executable).resolve().parent
        candidates: list[Path] = []
        for candidate in (compiled_root, executable_root):
            if candidate not in candidates:
                candidates.append(candidate)
        for candidate in candidates:
            if _is_complete_portable_root(candidate):
                return candidate
        # Keep Nuitka's authoritative location when the distribution is
        # incomplete so callers can produce a deterministic, actionable path.
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
