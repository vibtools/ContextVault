"""Path validation and filename sanitization utilities."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
_INVALID_FILENAME_CHARACTERS = re.compile(r"[<>:\"/\\|?*\x00-\x1F]")
_MULTIPLE_WHITESPACE = re.compile(r"\s+")


def sanitize_filename(value: str, *, fallback: str = "untitled", max_length: int = 120) -> str:
    """Return a portable Windows-safe file or directory name."""
    cleaned = _INVALID_FILENAME_CHARACTERS.sub("_", value)
    cleaned = _MULTIPLE_WHITESPACE.sub(" ", cleaned).strip(" .")
    if not cleaned:
        cleaned = fallback
    stem = Path(cleaned).stem.upper()
    if stem in _WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    if max_length < 1:
        raise ValueError("Maximum filename length must be at least 1.")
    if len(cleaned) > max_length:
        suffix = Path(cleaned).suffix
        if len(suffix) >= max_length:
            cleaned = cleaned[:max_length].rstrip(" .")
        else:
            available = max_length - len(suffix)
            cleaned = f"{cleaned[:available].rstrip(' .')}{suffix}"
    return cleaned or fallback


def ensure_within_root(path: Path, root: Path) -> Path:
    """Resolve *path* and reject traversal outside *root*."""
    resolved_root = root.expanduser().resolve()
    resolved_path = path.expanduser().resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Path escapes the allowed root: {path}") from exc
    return resolved_path


def validate_relative_archive_path(value: str) -> str:
    """Validate a portable POSIX relative archive reference."""
    if "\\" in value:
        raise ValueError("Archive paths must use forward slashes.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Unsafe archive path: {value}")
    return path.as_posix()


def unique_path(path: Path) -> Path:
    """Return an unused path by adding a numeric suffix when required."""
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
