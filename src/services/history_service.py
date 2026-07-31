"""Persistent export history service."""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config.constants import APPLICATION_VERSION, EXPORT_HISTORY_FILENAME
from src.utils.json_io import read_json, write_json
from src.utils.paths import data_directory

LOGGER = logging.getLogger(__name__)


class HistoryService:
    """Store export records in deterministic JSON with synchronized writes."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_directory() / EXPORT_HISTORY_FILENAME
        self._lock = threading.Lock()

    def list_records(self) -> list[dict[str, Any]]:
        """Return newest export records first."""
        with self._lock:
            if not self.path.exists():
                return []
            try:
                payload = read_json(self.path)
                records = payload.get("data", {}).get("records", [])
                if not isinstance(records, list):
                    return []
                return [record for record in records if isinstance(record, dict)]
            except (OSError, ValueError):
                LOGGER.exception("Unable to read export history")
                return []

    def append(self, record: dict[str, Any]) -> None:
        """Append one validated record and retain a bounded history."""
        with self._lock:
            records: list[dict[str, Any]] = []
            if self.path.exists():
                try:
                    payload = read_json(self.path)
                    existing = payload.get("data", {}).get("records", [])
                    if isinstance(existing, list):
                        records = [item for item in existing if isinstance(item, dict)]
                except (OSError, ValueError):
                    LOGGER.exception("Existing export history is invalid; rebuilding")
            records.insert(0, dict(record))
            records = records[:1000]
            payload = {
                "schemaVersion": "1.0",
                "format": "contextvault",
                "generatedBy": "ContextVault",
                "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "version": APPLICATION_VERSION,
                "data": {"records": records},
            }
            write_json(self.path, payload)
