"""Deterministic UTF-8 JSON read/write helpers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def write_json(path: Path, value: BaseModel | dict[str, Any], *, atomic: bool = True) -> None:
    """Write camelCase model data using UTF-8 and four-space indentation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value.model_dump(mode="json", by_alias=True, exclude_none=False) if isinstance(value, BaseModel) else value
    content = json.dumps(payload, ensure_ascii=False, indent=4, sort_keys=False) + "\n"
    if not atomic:
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
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    """Read and validate that a JSON file contains a root object."""
    with path.open("r", encoding="utf-8-sig") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload
