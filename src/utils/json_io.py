"""Deterministic UTF-8 JSON read/write helpers."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import weakref
from _thread import RLock as RLockType
from pathlib import Path
from typing import Any

from pydantic import BaseModel

_REPLACE_RETRY_DELAYS_SECONDS: tuple[float, ...] = (0.01, 0.02, 0.04, 0.08, 0.16)
_RETRYABLE_WINDOWS_REPLACE_ERRORS = frozenset({5, 32})
_PATH_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: weakref.WeakValueDictionary[str, RLockType] = weakref.WeakValueDictionary()


def _path_lock(path: Path) -> RLockType:
    """Return a process-local re-entrant lock for one normalized target path."""
    key = os.path.normcase(os.path.abspath(os.fspath(path)))
    with _PATH_LOCKS_GUARD:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _PATH_LOCKS[key] = lock
        return lock


def _is_retryable_replace_error(error: PermissionError) -> bool:
    """Return whether a replacement failure is a transient Windows sharing denial."""
    winerror = getattr(error, "winerror", None)
    return winerror in _RETRYABLE_WINDOWS_REPLACE_ERRORS or os.name == "nt"


def _replace_with_retry(source: Path, destination: Path) -> None:
    """Atomically replace a file, retrying bounded Windows sharing denials."""
    for delay in (*_REPLACE_RETRY_DELAYS_SECONDS, None):
        try:
            os.replace(source, destination)
            return
        except PermissionError as error:
            if delay is None or not _is_retryable_replace_error(error):
                raise
            time.sleep(delay)


def write_json(path: Path, value: BaseModel | dict[str, Any], *, atomic: bool = True) -> None:
    """Write camelCase model data using UTF-8 and four-space indentation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value.model_dump(mode="json", by_alias=True, exclude_none=False) if isinstance(value, BaseModel) else value
    content = json.dumps(payload, ensure_ascii=False, indent=4, sort_keys=False) + "\n"
    if not atomic:
        with _path_lock(path):
            path.write_text(content, encoding="utf-8", newline="\n")
        return

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        with _path_lock(path):
            _replace_with_retry(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    """Read and validate that a JSON file contains a root object."""
    with _path_lock(path):
        with path.open("r", encoding="utf-8-sig") as stream:
            payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload
