"""Atomic frozen-format archive generation engine."""

from __future__ import annotations

import hashlib
import io
import logging
import mimetypes
import shutil
import tempfile
import threading
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from PIL import Image, UnidentifiedImageError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config.constants import (
    APPLICATION_VERSION,
    ARCHIVE_FORMAT,
    ARCHIVE_SCHEMA_VERSION,
    CODE_EXTENSION_BY_LANGUAGE,
)
from src.core.archive_validator import ArchiveValidator
from src.core.rag_builder import RagBuilder
from src.models.archive import (
    ChunkMapDocument,
    ConversationData,
    ConversationDocument,
    FileHash,
    ManifestData,
    ManifestDocument,
    MetadataData,
    MetadataDocument,
    RagChunksDocument,
    RagDocumentsDocument,
    RagKeywordsDocument,
    SearchIndexDocument,
    StatisticsData,
    StatisticsDocument,
    SummaryData,
    SummaryDocument,
    ValidationStatus,
)
from src.models.conversation import ConversationRecord
from src.models.settings import ApplicationSettings
from src.parsers.search_index_builder import SearchIndexBuilder
from src.parsers.summary_builder import SummaryBuilder
from src.utils.json_io import write_json
from src.utils.security import sanitize_filename, unique_path

LOGGER = logging.getLogger(__name__)
ResourceLoader = Callable[[str], dict[str, Any]]
ProgressReporter = Callable[[str, float, str, int, int], None]


class ArchiveBuilder:
    """Build complete ContextVault archives through an atomic staging directory."""

    def __init__(self) -> None:
        self._summary_builder = SummaryBuilder()
        self._search_builder = SearchIndexBuilder()
        self._rag_builder = RagBuilder()
        self._validator = ArchiveValidator()

    def build(
        self,
        *,
        conversation: ConversationRecord,
        settings: ApplicationSettings,
        destination_root: Path,
        resource_loader: ResourceLoader,
        cancellation_event: threading.Event,
        progress_reporter: ProgressReporter | None = None,
    ) -> dict[str, Any]:
        """Generate, validate, and optionally compress one archive."""
        destination_root = destination_root.expanduser().resolve()
        if not destination_root.exists():
            if not settings.export.auto_create_folder:
                raise FileNotFoundError(f"Export directory does not exist: {destination_root}")
            destination_root.mkdir(parents=True, exist_ok=True)
        if not destination_root.is_dir():
            raise NotADirectoryError(f"Export destination is not a directory: {destination_root}")

        archive_name = self._archive_name(conversation, settings)
        final_root = destination_root / archive_name
        if final_root.exists() and not settings.export.overwrite:
            final_root = unique_path(final_root)
        staging_root = destination_root / f".{final_root.name}.partial-{uuid4().hex}"
        staging_root.mkdir(parents=False, exist_ok=False)
        export_log: list[str] = []
        try:
            self._create_structure(staging_root)
            self._log(export_log, "Archive staging directory created")
            self._check_cancelled(cancellation_event)
            self._extract_assets(
                conversation=conversation,
                settings=settings,
                root=staging_root,
                resource_loader=resource_loader,
                cancellation_event=cancellation_event,
                progress_reporter=progress_reporter,
                export_log=export_log,
            )
            self._check_cancelled(cancellation_event)
            generated_at = datetime.now(UTC)
            search_index = self._search_builder.build(conversation)
            summary = self._summary_builder.build(conversation)
            if not settings.assets.summary:
                summary = SummaryData(
                    short_summary="Summary generation disabled by export settings.",
                    long_summary="Summary generation disabled by export settings.",
                )
            if not settings.assets.search_index:
                search_index.keywords = []
                search_index.topics = []
                search_index.important_terms = []
                search_index.entity_mapping = {}
                search_index.message_mapping = []
            documents = self._build_documents(conversation, summary, search_index, generated_at)
            self._write_documents(staging_root, documents)
            self._write_markdown(staging_root, conversation, rich_markdown=settings.assets.markdown)
            self._write_rag_documents(staging_root, conversation, search_index, generated_at)
            for warning in conversation.capture_warnings:
                self._log(export_log, f"WARNING: {warning}")
            self._log(export_log, "Conversation documents generated")
            (staging_root / "logs" / "export.log").write_text("\n".join(export_log) + "\n", encoding="utf-8", newline="\n")

            manifest = self._manifest(
                conversation,
                generated_at,
                [],
                None,
                message_retry_count=settings.performance.message_retry_count,
            )
            write_json(staging_root / "manifest.json", manifest)
            (staging_root / "logs" / "validation.log").write_text(
                "status=PENDING\ncheckedFiles=0\n",
                encoding="utf-8",
                newline="\n",
            )
            preliminary = self._validator.validate(staging_root, verify_hashes=False)
            self._write_validation_log(staging_root, preliminary)
            manifest.data.hash_information = self._hash_archive_files(staging_root)
            manifest.data.validation_status = ValidationStatus(
                status="valid" if preliminary.is_valid else "invalid",
                validated_at=datetime.now(UTC),
                errors=preliminary.errors,
                warnings=preliminary.warnings,
            )
            write_json(staging_root / "manifest.json", manifest)
            final_validation = self._validator.validate(staging_root, verify_hashes=True)
            self._write_validation_log(staging_root, final_validation)
            manifest.data.validation_status = ValidationStatus(
                status="valid" if final_validation.is_valid else "invalid",
                validated_at=datetime.now(UTC),
                errors=final_validation.errors,
                warnings=final_validation.warnings,
            )
            write_json(staging_root / "manifest.json", manifest)
            if settings.export.verify_export and not final_validation.is_valid:
                raise RuntimeError("Archive validation failed: " + "; ".join(final_validation.errors))
            self._check_cancelled(cancellation_event)
            self._publish_staging(
                staging_root,
                final_root,
                destination_root,
                overwrite=settings.export.overwrite,
            )
            zip_path: Path | None = None
            if settings.export.compress:
                zip_path = self._compress(
                    final_root,
                    cancellation_event,
                    overwrite=settings.export.overwrite,
                )
            if progress_reporter is not None:
                progress_reporter("Archive complete", 100.0, final_root.name, 1, 1)
            LOGGER.info("Archive created: %s", final_root)
            return {
                "archivePath": str(final_root),
                "zipPath": str(zip_path) if zip_path else "",
                "conversationId": conversation.conversation_id,
                "title": conversation.title,
                "messageCount": len(conversation.messages),
                "validation": final_validation.model_dump(mode="json", by_alias=True),
            }
        except Exception:
            if staging_root.exists():
                shutil.rmtree(staging_root, ignore_errors=True)
            raise

    @staticmethod
    def _create_structure(root: Path) -> None:
        for relative in (
            "assets/code",
            "assets/images",
            "assets/attachments",
            "assets/tables",
            "assets/citations",
            "rag",
            "logs",
        ):
            (root / relative).mkdir(parents=True, exist_ok=True)

    def _extract_assets(
        self,
        *,
        conversation: ConversationRecord,
        settings: ApplicationSettings,
        root: Path,
        resource_loader: ResourceLoader,
        cancellation_event: threading.Event,
        progress_reporter: ProgressReporter | None,
        export_log: list[str],
    ) -> None:
        total = sum(
            len(message.code_references)
            + len(message.image_references)
            + len(message.attachment_references)
            + len(message.table_references)
            + len(message.citation_references)
            for message in conversation.messages
        )
        completed = 0
        for message in conversation.messages:
            self._check_cancelled(cancellation_event)
            if settings.assets.code:
                for code in message.code_references:
                    extension = CODE_EXTENSION_BY_LANGUAGE.get(code.language.lower(), ".txt")
                    filename = sanitize_filename(f"{message.sequence_number:04d}-{code.id}{extension}")
                    relative = Path("assets/code") / filename
                    self._write_verified_bytes(
                        root / relative,
                        code.raw_code.encode("utf-8"),
                        attempts=settings.performance.message_retry_count + 1,
                        description=f"code reference {code.id}",
                    )
                    code.file_path = relative.as_posix()
                    completed = self._asset_progress(progress_reporter, completed, total, "Code", filename)
            else:
                completed += len(message.code_references)

            if settings.assets.tables:
                for table in message.table_references:
                    base = sanitize_filename(f"{message.sequence_number:04d}-{table.id}")
                    json_relative = Path("assets/tables") / f"{base}.json"
                    html_relative = Path("assets/tables") / f"{base}.html"
                    markdown_relative = Path("assets/tables") / f"{base}.md"
                    write_json(
                        root / json_relative,
                        {
                            "schemaVersion": ARCHIVE_SCHEMA_VERSION,
                            "format": ARCHIVE_FORMAT,
                            "generatedBy": "ContextVault",
                            "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                            "version": APPLICATION_VERSION,
                            "data": {"headers": table.headers, "rows": table.rows},
                        },
                    )
                    (root / html_relative).write_text(table.html, encoding="utf-8", newline="\n")
                    (root / markdown_relative).write_text(table.markdown + "\n", encoding="utf-8", newline="\n")
                    table.json_file_path = json_relative.as_posix()
                    table.html_file_path = html_relative.as_posix()
                    table.markdown_file_path = markdown_relative.as_posix()
                    completed = self._asset_progress(progress_reporter, completed, total, "Table", base)
            else:
                completed += len(message.table_references)

            for citation in message.citation_references:
                filename = sanitize_filename(f"{message.sequence_number:04d}-{citation.id}.json")
                relative = Path("assets/citations") / filename
                write_json(
                    root / relative,
                    {
                        "schemaVersion": ARCHIVE_SCHEMA_VERSION,
                        "format": ARCHIVE_FORMAT,
                        "generatedBy": "ContextVault",
                        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                        "version": APPLICATION_VERSION,
                        "data": {"id": citation.id, "url": citation.url, "label": citation.label},
                    },
                )
                citation.file_path = relative.as_posix()
                completed = self._asset_progress(progress_reporter, completed, total, "Citation", filename)

            if settings.assets.images:
                for image_reference in message.image_references:
                    payload = resource_loader(image_reference.source_url)
                    data = _payload_bytes(payload)
                    media_type = str(payload.get("contentType") or "")
                    image_format, width, height = _inspect_image(data)
                    extension = _image_extension(image_format, media_type, image_reference.source_url)
                    filename = sanitize_filename(f"{message.sequence_number:04d}-{image_reference.id}{extension}")
                    relative = Path("assets/images") / filename
                    self._write_verified_bytes(
                        root / relative,
                        data,
                        attempts=settings.performance.message_retry_count + 1,
                        description=f"image reference {image_reference.id}",
                    )
                    image_reference.file_path = relative.as_posix()
                    image_reference.media_type = media_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
                    image_reference.width = width
                    image_reference.height = height
                    image_reference.file_size = len(data)
                    image_reference.sha256 = hashlib.sha256(data).hexdigest()
                    completed = self._asset_progress(progress_reporter, completed, total, "Image", filename)
            else:
                completed += len(message.image_references)

            if settings.assets.attachments:
                for attachment in message.attachment_references:
                    payload = resource_loader(attachment.source_url)
                    data = _payload_bytes(payload)
                    suggested = str(payload.get("suggestedFilename") or attachment.original_name or "attachment")
                    filename = sanitize_filename(suggested)
                    relative = Path("assets/attachments") / filename
                    target = root / relative
                    if target.exists():
                        target = unique_path(target)
                        relative = target.relative_to(root)
                    self._write_verified_bytes(
                        target,
                        data,
                        attempts=settings.performance.message_retry_count + 1,
                        description=f"attachment reference {attachment.id}",
                    )
                    attachment.file_path = relative.as_posix()
                    attachment.original_name = attachment.original_name or filename
                    attachment.media_type = str(payload.get("contentType") or mimetypes.guess_type(filename)[0] or "application/octet-stream")
                    attachment.file_size = len(data)
                    attachment.sha256 = hashlib.sha256(data).hexdigest()
                    completed = self._asset_progress(progress_reporter, completed, total, "Attachment", filename)
            else:
                completed += len(message.attachment_references)
        self._log(export_log, f"Assets processed: {completed}/{total}")

    @staticmethod
    def _asset_progress(
        reporter: ProgressReporter | None,
        completed: int,
        total: int,
        stage: str,
        item: str,
    ) -> int:
        completed += 1
        if reporter is not None:
            percentage = 20.0 + (completed / max(total, 1)) * 45.0
            reporter(f"Processing {stage.lower()}", percentage, item, completed, total)
        return completed

    @staticmethod
    def _write_verified_bytes(target: Path, data: bytes, *, attempts: int, description: str) -> None:
        """Atomically persist bytes and verify the exact payload immediately."""
        target.parent.mkdir(parents=True, exist_ok=True)
        retrying = Retrying(
            retry=retry_if_exception_type((OSError, RuntimeError)),
            stop=stop_after_attempt(max(1, attempts)),
            wait=wait_exponential(multiplier=0.05, min=0.05, max=0.8),
            reraise=True,
        )
        for attempt in retrying:
            with attempt:
                temporary: Path | None = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="wb",
                        prefix=".cv-",
                        suffix=".tmp",
                        dir=target.parent,
                        delete=False,
                    ) as stream:
                        temporary = Path(stream.name)
                        stream.write(data)
                    if temporary.read_bytes() != data:
                        raise RuntimeError(f"Immediate byte verification failed for {description}.")
                    temporary.replace(target)
                    if target.read_bytes() != data:
                        raise RuntimeError(f"Published byte verification failed for {description}.")
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)

    def _build_documents(
        self,
        conversation: ConversationRecord,
        summary: SummaryData,
        search_index: Any,
        generated_at: datetime,
    ) -> dict[str, Any]:
        user_messages = sum(message.role == "user" for message in conversation.messages)
        assistant_messages = sum(message.role == "assistant" for message in conversation.messages)
        total_characters = sum(message.character_count for message in conversation.messages)
        total_words = sum(message.word_count for message in conversation.messages)
        total_tokens = sum(message.estimated_tokens for message in conversation.messages)
        image_count = sum(len(message.image_references) for message in conversation.messages)
        attachment_count = sum(len(message.attachment_references) for message in conversation.messages)
        code_count = sum(len(message.code_references) for message in conversation.messages)
        table_count = sum(len(message.table_references) for message in conversation.messages)
        skipped_count = sum(message.capture_status == "skipped" for message in conversation.messages)
        statistics = StatisticsData(
            total_messages=len(conversation.messages),
            user_messages=user_messages,
            assistant_messages=assistant_messages,
            images=image_count,
            attachments=attachment_count,
            code_blocks=code_count,
            tables=table_count,
            citations=sum(len(message.citation_references) for message in conversation.messages),
            total_characters=total_characters,
            total_words=total_words,
            estimated_tokens=total_tokens,
        )
        return {
            "conversation": ConversationDocument(
                generated_at=generated_at,
                data=ConversationData(
                    conversation_id=conversation.conversation_id,
                    title=conversation.title,
                    url=conversation.url,
                    platform_name=conversation.platform_name,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                    exported_at=conversation.exported_at,
                    timezone=conversation.timezone,
                    timestamp_source=conversation.timestamp_source,
                    messages=conversation.messages,
                ),
            ),
            "metadata": MetadataDocument(
                generated_at=generated_at,
                data=MetadataData(
                    conversation_title=conversation.title,
                    conversation_url=conversation.url,
                    conversation_id=conversation.conversation_id,
                    platform_name=conversation.platform_name,
                    export_date=conversation.exported_at,
                    created_date=conversation.created_at,
                    updated_date=conversation.updated_at,
                    export_timestamp_utc=conversation.exported_at,
                    export_timestamp_local=conversation.exported_at_local,
                    timezone=conversation.timezone,
                    timestamp_source=conversation.timestamp_source,
                    duration_seconds=conversation.duration_seconds,
                    export_uuid=conversation.export_id,
                    contextvault_version=APPLICATION_VERSION,
                    export_engine_version=APPLICATION_VERSION,
                    schema_version=ARCHIVE_SCHEMA_VERSION,
                    browser_name=conversation.browser_name,
                    browser_version=conversation.browser_version,
                    browser_profile=conversation.browser_profile,
                    chatgpt_workspace=conversation.chatgpt_workspace,
                    chatgpt_model=conversation.chatgpt_model,
                    images=image_count,
                    attachments=attachment_count,
                    code_blocks=code_count,
                    tables=table_count,
                    estimated_size=conversation.estimated_size,
                    skipped_messages=skipped_count,
                    capture_warnings=conversation.capture_warnings,
                    language=conversation.language,
                    total_messages=len(conversation.messages),
                    user_messages=user_messages,
                    assistant_messages=assistant_messages,
                    character_count=total_characters,
                    word_count=total_words,
                    estimated_token_count=total_tokens,
                ),
            ),
            "summary": SummaryDocument(generated_at=generated_at, data=summary),
            "search": SearchIndexDocument(generated_at=generated_at, data=search_index),
            "statistics": StatisticsDocument(generated_at=generated_at, data=statistics),
        }

    @staticmethod
    def _write_documents(root: Path, documents: dict[str, Any]) -> None:
        write_json(root / "conversation.json", documents["conversation"])
        write_json(root / "metadata.json", documents["metadata"])
        write_json(root / "summary.json", documents["summary"])
        write_json(root / "search-index.json", documents["search"])
        write_json(root / "statistics.json", documents["statistics"])

    @staticmethod
    def _write_markdown(root: Path, conversation: ConversationRecord, *, rich_markdown: bool) -> None:
        output = [f"# {conversation.title}", "", f"Source: {conversation.url}", ""]
        for message in conversation.messages:
            timestamp = message.timestamp or message.captured_at
            timestamp_line = timestamp.isoformat() if timestamp is not None else "unknown"
            capture_suffix = " [DEGRADED]" if message.capture_status == "skipped" else ""
            output.extend(
                [
                    f"## {message.role.title()} — Message {message.sequence_number}{capture_suffix}",
                    "",
                    f"Timestamp: {timestamp_line}",
                    "",
                    message.markdown if rich_markdown else message.plain_text,
                    "",
                ]
            )
        (root / "conversation.md").write_text("\n".join(output).rstrip() + "\n", encoding="utf-8", newline="\n")

    def _write_rag_documents(self, root: Path, conversation: ConversationRecord, search_index: Any, generated_at: datetime) -> None:
        chunks, documents, keywords, chunk_map = self._rag_builder.build(conversation, search_index)
        write_json(root / "rag/chunks.json", RagChunksDocument(generated_at=generated_at, data=chunks))
        write_json(root / "rag/documents.json", RagDocumentsDocument(generated_at=generated_at, data=documents))
        write_json(root / "rag/keywords.json", RagKeywordsDocument(generated_at=generated_at, data=keywords))
        write_json(root / "rag/chunk-map.json", ChunkMapDocument(generated_at=generated_at, data=chunk_map))

    @staticmethod
    def _hash_archive_files(root: Path) -> list[FileHash]:
        entries: list[FileHash] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if relative == "manifest.json" or relative.startswith("logs/"):
                continue
            data = path.read_bytes()
            entries.append(FileHash(path=relative, sha256=hashlib.sha256(data).hexdigest(), size=len(data)))
        return entries

    @staticmethod
    def _manifest(
        conversation: ConversationRecord,
        generated_at: datetime,
        hashes: list[FileHash],
        validation: Any | None,
        *,
        message_retry_count: int,
    ) -> ManifestDocument:
        return ManifestDocument(
            generated_at=generated_at,
            data=ManifestData(
                archive_id=str(uuid4()),
                archive_version=APPLICATION_VERSION,
                archive_format_version=ARCHIVE_SCHEMA_VERSION,
                export_date=conversation.exported_at,
                conversation_id=conversation.conversation_id,
                conversation_title=conversation.title,
                conversation_started_at=conversation.created_at,
                conversation_ended_at=conversation.updated_at,
                exported_at=conversation.exported_at,
                timezone=conversation.timezone,
                timestamp_source=conversation.timestamp_source,
                duration_seconds=conversation.duration_seconds,
                total_messages=len(conversation.messages),
                verified_messages=sum(message.capture_status == "verified" for message in conversation.messages),
                skipped_messages=sum(message.capture_status == "skipped" for message in conversation.messages),
                message_retry_count=message_retry_count,
                incremental_verification=bool(conversation.readiness.get("incrementalVerification")),
                file_mapping={
                    "conversation": "conversation.json",
                    "markdown": "conversation.md",
                    "metadata": "metadata.json",
                    "summary": "summary.json",
                    "searchIndex": "search-index.json",
                    "statistics": "statistics.json",
                },
                folder_mapping={
                    "assets": "assets/",
                    "rag": "rag/",
                    "logs": "logs/",
                },
                hash_information=hashes,
                validation_status=(
                    ValidationStatus(status="notValidated")
                    if validation is None
                    else ValidationStatus(
                        status="valid" if validation.is_valid else "invalid",
                        validated_at=datetime.now(UTC),
                        errors=validation.errors,
                        warnings=validation.warnings,
                    )
                ),
            ),
        )

    @staticmethod
    def _write_validation_log(root: Path, validation: Any) -> None:
        lines = [
            f"status={'PASS' if validation.is_valid else 'FAIL'}",
            f"checkedFiles={validation.checked_files}",
        ]
        lines.extend(f"ERROR: {error}" for error in validation.errors)
        lines.extend(f"WARNING: {warning}" for warning in validation.warnings)
        (root / "logs/validation.log").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    @staticmethod
    def _archive_name(conversation: ConversationRecord, settings: ApplicationSettings) -> str:
        pattern = settings.export.archive_name
        value = (
            pattern.replace("{title}", conversation.title)
            .replace("{id}", conversation.conversation_id)
            .replace("{date}", conversation.exported_at.strftime("%Y-%m-%d"))
        )
        return sanitize_filename(value, fallback=f"ContextVault-{conversation.conversation_id}")

    @staticmethod
    def _publish_staging(
        staging_root: Path,
        final_root: Path,
        allowed_parent: Path,
        *,
        overwrite: bool,
    ) -> None:
        """Publish a validated archive without destroying the previous version on failure."""
        parent = allowed_parent.resolve()
        if staging_root.parent.resolve() != parent or final_root.parent.resolve() != parent:
            raise ValueError("Refusing to publish an archive outside the configured export root.")
        if staging_root.is_symlink() or final_root.is_symlink():
            raise ValueError("Refusing to publish through a symbolic link.")

        backup_root: Path | None = None
        if final_root.exists():
            if not overwrite:
                raise FileExistsError(f"Archive already exists: {final_root}")
            if not final_root.is_dir():
                raise ValueError(f"Refusing to overwrite a non-directory archive target: {final_root}")
            backup_root = parent / f".{final_root.name}.backup-{uuid4().hex}"
            final_root.replace(backup_root)

        try:
            staging_root.replace(final_root)
        except Exception:
            if backup_root is not None and backup_root.exists() and not final_root.exists():
                backup_root.replace(final_root)
            raise
        if backup_root is not None and backup_root.exists():
            try:
                shutil.rmtree(backup_root)
            except OSError:
                LOGGER.warning("Unable to remove replaced archive backup: %s", backup_root, exc_info=True)

    @staticmethod
    def _compress(
        root: Path,
        cancellation_event: threading.Event,
        *,
        overwrite: bool,
    ) -> Path:
        zip_path = root.with_suffix(".zip")
        if zip_path.exists() and not overwrite:
            zip_path = unique_path(zip_path)
        temporary = zip_path.parent / f".{zip_path.name}.partial-{uuid4().hex}"
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for path in sorted(root.rglob("*")):
                    if cancellation_event.is_set():
                        raise InterruptedError("Archive compression cancelled.")
                    if path.is_file():
                        archive.write(path, arcname=(Path(root.name) / path.relative_to(root)).as_posix())
            temporary.replace(zip_path)
            return zip_path
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _check_cancelled(event: threading.Event) -> None:
        if event.is_set():
            raise InterruptedError("Archive generation cancelled.")

    @staticmethod
    def _log(output: list[str], message: str) -> None:
        output.append(f"{datetime.now(UTC).isoformat().replace('+00:00', 'Z')} {message}")


def _payload_bytes(payload: dict[str, Any]) -> bytes:
    value = payload.get("content")
    if not isinstance(value, (bytes, bytearray)):
        raise TypeError("Resource loader returned non-binary content.")
    return bytes(value)


def _inspect_image(data: bytes) -> tuple[str, int, int]:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            return (image.format or "PNG", image.width, image.height)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Downloaded image is invalid or corrupted.") from exc


def _image_extension(image_format: str, media_type: str, source_url: str) -> str:
    by_format = {
        "JPEG": ".jpg",
        "PNG": ".png",
        "WEBP": ".webp",
        "GIF": ".gif",
        "BMP": ".bmp",
    }
    if image_format.upper() in by_format:
        return by_format[image_format.upper()]
    guessed = mimetypes.guess_extension(media_type, strict=False)
    if guessed:
        return guessed
    source_suffix = Path(source_url.split("?", 1)[0]).suffix.lower()
    return source_suffix if source_suffix else ".bin"
