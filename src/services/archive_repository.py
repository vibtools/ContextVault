"""Archive discovery and management operations."""

from __future__ import annotations

import hashlib
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core.archive_validator import ArchiveValidator
from src.models.archive import ConversationDocument, FileHash, ManifestDocument, SummaryDocument, ValidationStatus
from src.models.conversation import ConversationRecord
from src.parsers.summary_builder import SummaryBuilder
from src.utils.json_io import read_json, write_json
from src.utils.security import ensure_within_root
from src.utils.system import open_path

LOGGER = logging.getLogger(__name__)


class ArchiveRepository:
    """Manage generated archive folders without implementing an in-app viewer."""

    def __init__(self) -> None:
        self._validator = ArchiveValidator()
        self._summary_builder = SummaryBuilder()

    def list_archives(self, export_root: Path) -> list[dict[str, Any]]:
        """Discover valid-looking archive folders under the configured export root."""
        root = export_root.expanduser().resolve()
        if not root.exists():
            return []
        output: list[dict[str, Any]] = []
        for manifest_path in sorted(root.glob("*/manifest.json"), key=lambda path: path.stat().st_mtime, reverse=True):
            try:
                payload = read_json(manifest_path)
                data = payload.get("data", {})
                if not isinstance(data, dict):
                    continue
                archive_root = manifest_path.parent
                output.append(
                    {
                        "name": archive_root.name,
                        "path": str(archive_root),
                        "title": str(data.get("conversationTitle") or archive_root.name),
                        "conversationId": str(data.get("conversationId") or ""),
                        "exportDate": str(data.get("exportDate") or ""),
                        "status": str((data.get("validationStatus") or {}).get("status") or "unknown"),
                        "size": sum(path.stat().st_size for path in archive_root.rglob("*") if path.is_file()),
                    }
                )
            except (OSError, ValueError):
                LOGGER.exception("Failed to inspect archive manifest: %s", manifest_path)
        return output

    def validate(self, archive_path: Path) -> dict[str, Any]:
        """Validate one archive and return a serializable result."""
        return self._validator.validate(archive_path).model_dump(mode="json", by_alias=True)

    def open_archive(self, archive_path: Path) -> bool:
        """Open conversation.md using the operating-system handler."""
        target = archive_path / "conversation.md"
        return open_path(target)

    def open_folder(self, archive_path: Path) -> bool:
        """Open an archive directory using the operating-system handler."""
        return open_path(archive_path)

    def delete_archive(self, archive_path: Path, export_root: Path) -> None:
        """Delete one direct-child archive after strict path validation."""
        root = export_root.expanduser().resolve()
        target = ensure_within_root(archive_path, root)
        if target.parent != root or not target.is_dir():
            raise ValueError("Only direct archive folders inside the export root may be deleted.")
        if not (target / "manifest.json").is_file():
            raise ValueError("Refusing to delete a folder that is not a ContextVault archive.")
        shutil.rmtree(target)
        LOGGER.info("Archive deleted: %s", target)

    def rebuild_summary(self, archive_path: Path) -> dict[str, Any]:
        """Regenerate summary.json from the frozen conversation.json source."""
        root = archive_path.expanduser().resolve()
        document = ConversationDocument.model_validate(read_json(root / "conversation.json"))
        conversation = ConversationRecord(
            conversation_id=document.data.conversation_id,
            title=document.data.title,
            url=document.data.url,
            platform_name=document.data.platform_name,
            created_at=document.data.created_at,
            exported_at=document.generated_at,
            language="unknown",
            messages=document.data.messages,
        )
        summary = self._summary_builder.build(conversation)
        summary_document = SummaryDocument(generated_at=datetime.now(UTC), data=summary)
        summary_path = root / "summary.json"
        write_json(summary_path, summary_document)

        manifest_path = root / "manifest.json"
        manifest = ManifestDocument.model_validate(read_json(manifest_path))
        self._replace_manifest_hash(manifest, root, summary_path)
        manifest.data.validation_status = ValidationStatus(status="notValidated")
        write_json(manifest_path, manifest)

        validation = self._validator.validate(root)
        manifest.data.validation_status = ValidationStatus(
            status="valid" if validation.is_valid else "invalid",
            validated_at=datetime.now(UTC),
            errors=validation.errors,
            warnings=validation.warnings,
        )
        write_json(manifest_path, manifest)
        self._write_validation_log(root, validation)
        LOGGER.info("Summary rebuilt: %s", root)
        return {
            "archivePath": str(root),
            "validation": validation.model_dump(mode="json", by_alias=True),
        }

    @staticmethod
    def _replace_manifest_hash(manifest: ManifestDocument, root: Path, target: Path) -> None:
        relative = target.relative_to(root).as_posix()
        content = target.read_bytes()
        replacement = FileHash(
            path=relative,
            sha256=hashlib.sha256(content).hexdigest(),
            size=len(content),
        )
        entries = [entry for entry in manifest.data.hash_information if entry.path != relative]
        entries.append(replacement)
        manifest.data.hash_information = sorted(entries, key=lambda entry: entry.path)

    @staticmethod
    def _write_validation_log(root: Path, validation: Any) -> None:
        lines = [
            f"status={'PASS' if validation.is_valid else 'FAIL'}",
            f"checkedFiles={validation.checked_files}",
        ]
        lines.extend(f"ERROR: {error}" for error in validation.errors)
        lines.extend(f"WARNING: {warning}" for warning in validation.warnings)
        (root / "logs" / "validation.log").write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
            newline="\n",
        )
