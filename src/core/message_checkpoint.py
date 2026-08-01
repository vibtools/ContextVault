"""Incremental per-message capture, persistence, and verification support."""

from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config.constants import (
    APPLICATION_VERSION,
    ARCHIVE_FORMAT,
    ARCHIVE_SCHEMA_VERSION,
    CODE_EXTENSION_BY_LANGUAGE,
)
from src.models.conversation import ConversationMessage
from src.parsers.conversation_parser import ConversationParser
from src.utils.json_io import read_json, write_json
from src.utils.text import estimated_tokens, word_count

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class MessageCheckpointResult:
    """Result returned to the browser deep-scan loop for one settled DOM window."""

    verified_keys: list[str] = field(default_factory=list)
    skipped_keys: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "verifiedKeys": list(self.verified_keys),
            "skippedKeys": list(self.skipped_keys),
            "failed": dict(self.failed),
        }




class MessageCheckpointInfrastructureError(RuntimeError):
    """Raised when durable checkpoint storage or verification fails."""


class MessageCheckpointStore:
    """Persist and verify each message before browser scrolling continues."""

    def __init__(self, root: Path, *, conversation_id: str, base_url: str) -> None:
        self.root = root.resolve()
        self.conversation_id = conversation_id
        self.base_url = base_url
        self._parser = ConversationParser()
        self._messages_by_key: dict[str, ConversationMessage] = {}
        self._signatures_by_key: dict[str, str] = {}
        self._attempts_by_key: dict[str, int] = {}
        self._errors_by_key: dict[str, str] = {}
        self._warnings_by_key: dict[str, str] = {}
        self._messages_root = self.root / "messages"
        self._code_root = self.root / "code"
        self._messages_root.mkdir(parents=True, exist_ok=False)
        self._code_root.mkdir(parents=True, exist_ok=False)

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings_by_key.values())

    @property
    def verified_count(self) -> int:
        return sum(message.capture_status == "verified" for message in self._messages_by_key.values())

    @property
    def skipped_count(self) -> int:
        return sum(message.capture_status == "skipped" for message in self._messages_by_key.values())

    def capture_window(
        self,
        items: list[dict[str, Any]],
        order: tuple[str, ...],
        skip_keys: set[str],
    ) -> dict[str, Any]:
        """Parse, save, and immediately verify one stable virtualized DOM window."""
        result = MessageCheckpointResult()
        sequence_by_key = {key: index + 1 for index, key in enumerate(order)}
        for index, item in enumerate(items, start=1):
            key = str(item.get("key") or "").strip()
            signature = str(item.get("signature") or "").strip()
            html = str(item.get("html") or "")
            if not key:
                result.failed[f"window-item-{index}"] = "Observed message has no stable checkpoint key."
                continue
            if not signature:
                result.failed[key] = "Observed message has no content signature."
                continue
            if not html:
                result.failed[key] = "Observed message has no serializable HTML."
                continue
            if self._signatures_by_key.get(key) == signature and key in self._messages_by_key:
                existing = self._messages_by_key[key]
                if existing.capture_status == "skipped":
                    result.skipped_keys.append(key)
                else:
                    result.verified_keys.append(key)
                continue

            sequence_number = sequence_by_key.get(key, max(1, int(item.get("domIndex", 0)) + 1))
            captured_at = _parse_datetime(item.get("capturedAt")) or datetime.now(UTC)
            if key in skip_keys:
                attempt = max(1, self._attempts_by_key.get(key, 0))
                reason = self._errors_by_key.get(key, "Configured message retries were exhausted.")
                message = self._degraded_message(item, sequence_number, attempt, captured_at, reason)
                try:
                    self._persist_and_verify(key, message)
                except (OSError, RuntimeError, ValueError) as exc:
                    raise MessageCheckpointInfrastructureError(
                        f"Unable to persist degraded checkpoint for {key}: {exc}"
                    ) from exc
                warning = (
                    f"Message {key} was preserved as a degraded placeholder after {attempt} capture attempt(s): {reason}"
                )
                self._warnings_by_key[key] = warning
                LOGGER.error(warning)
                result.skipped_keys.append(key)
            else:
                attempt = self._attempts_by_key.get(key, 0) + 1
                self._attempts_by_key[key] = attempt
                try:
                    message = self._parser.parse_message_fragment(
                        html=html,
                        sequence_number=sequence_number,
                        conversation_id=self.conversation_id,
                        base_url=self.base_url,
                        captured_at=captured_at,
                        source_key=key,
                        source_signature=signature,
                        capture_attempts=attempt,
                    )
                    source_timestamp = _parse_datetime(item.get("timestamp"))
                    if message.timestamp is None and source_timestamp is not None:
                        message.timestamp = source_timestamp
                        message.timestamp_source = "message_timestamp"
                except Exception as exc:
                    reason = f"{type(exc).__name__}: {exc}"
                    self._errors_by_key[key] = reason
                    LOGGER.warning(
                        "Message checkpoint parsing failed key=%s attempt=%s: %s",
                        key,
                        attempt,
                        reason,
                    )
                    result.failed[key] = reason
                    continue
                try:
                    self._persist_and_verify(key, message)
                except (OSError, RuntimeError, ValueError) as exc:
                    raise MessageCheckpointInfrastructureError(
                        f"Unable to persist and verify checkpoint for {key}: {exc}"
                    ) from exc
                else:
                    self._errors_by_key.pop(key, None)
                    self._warnings_by_key.pop(key, None)
                    result.verified_keys.append(key)

            self._messages_by_key[key] = message
            self._signatures_by_key[key] = signature
        return result.as_dict()

    def ordered_messages(self, order: tuple[str, ...]) -> list[ConversationMessage]:
        """Return all verified/degraded messages in global conversation order."""
        missing = [key for key in order if key not in self._messages_by_key]
        if missing:
            raise RuntimeError(f"Incremental message checkpoints are missing {len(missing)} message(s): {missing[:5]}")
        return [self._messages_by_key[key].model_copy(deep=True) for key in order]

    def close(self) -> None:
        """Delete temporary checkpoint files and report cleanup failures."""
        if not self.root.exists():
            return
        try:
            shutil.rmtree(self.root)
        except OSError:
            LOGGER.warning(
                "Unable to remove temporary message checkpoint directory: %s",
                self.root,
                exc_info=True,
            )

    def _persist_and_verify(self, key: str, message: ConversationMessage) -> None:
        digest = hashlib.sha256(key.encode("utf-8", errors="surrogatepass")).hexdigest()[:24]
        message_path = self._messages_root / f"{digest}.json"
        payload = {
            "schemaVersion": ARCHIVE_SCHEMA_VERSION,
            "format": ARCHIVE_FORMAT,
            "generatedBy": "ContextVault",
            "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "version": APPLICATION_VERSION,
            "data": message.model_dump(mode="json", by_alias=True),
        }
        write_json(message_path, payload)
        round_trip = read_json(message_path)
        restored = ConversationMessage.model_validate(round_trip.get("data"))
        if restored.model_dump(mode="json", by_alias=True) != message.model_dump(mode="json", by_alias=True):
            raise RuntimeError("Message JSON round-trip verification failed.")

        for index, code in enumerate(message.code_references, start=1):
            extension = CODE_EXTENSION_BY_LANGUAGE.get(code.language.lower(), ".txt")
            code_path = self._code_root / f"{digest}-{index:03d}{extension}"
            expected = code.raw_code.encode("utf-8")
            code_path.write_bytes(expected)
            actual = code_path.read_bytes()
            if actual != expected:
                raise RuntimeError(f"Code checkpoint byte verification failed for {code.id}.")
            try:
                actual.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise RuntimeError(f"Code checkpoint is not valid UTF-8 for {code.id}.") from exc

    @staticmethod
    def _degraded_message(
        item: dict[str, Any],
        sequence_number: int,
        attempt: int,
        captured_at: datetime,
        reason: str,
    ) -> ConversationMessage:
        key = str(item.get("key") or f"skipped-{sequence_number}")
        role = str(item.get("role") or "unknown").lower()
        if role not in {"user", "assistant", "system", "tool", "unknown"}:
            role = "unknown"
        text = str(item.get("text") or "").strip()
        if not text:
            text = f"[ContextVault could not capture this message after {attempt} attempt(s).]"
        source_timestamp = _parse_datetime(item.get("timestamp"))
        return ConversationMessage(
            message_id=key,
            sequence_number=sequence_number,
            role=role,
            plain_text=text,
            markdown=text,
            html="",
            timestamp=source_timestamp,
            captured_at=captured_at,
            timestamp_source="message_timestamp" if source_timestamp is not None else "unknown",
            capture_status="skipped",
            capture_attempts=attempt,
            capture_error=reason,
            source_key=key,
            source_signature=str(item.get("signature") or ""),
            character_count=len(text),
            word_count=word_count(text),
            estimated_tokens=estimated_tokens(text),
        )


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        numeric = float(text)
    except ValueError:
        numeric = None
    if numeric is not None:
        if numeric > 10_000_000_000:
            numeric /= 1000.0
        try:
            return datetime.fromtimestamp(numeric, UTC)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
