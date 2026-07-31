"""Forensic archive structure, schema, reference, and integrity validator."""

from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from src.config.constants import (
    APPLICATION_VERSION,
    ARCHIVE_FORMAT,
    ARCHIVE_SCHEMA_VERSION,
    REQUIRED_ARCHIVE_DIRECTORIES,
    REQUIRED_ARCHIVE_FILES,
)
from src.models.archive import (
    ArchiveValidationResult,
    ChunkMapDocument,
    ConversationDocument,
    ManifestDocument,
    MetadataDocument,
    RagChunksDocument,
    RagDocumentsDocument,
    RagKeywordsDocument,
    SearchIndexDocument,
    StatisticsDocument,
    SummaryDocument,
)
from src.utils.json_io import read_json
from src.utils.security import ensure_within_root, validate_relative_archive_path
from src.utils.text import estimated_tokens, word_count

LOGGER = logging.getLogger(__name__)

_DOCUMENT_MODELS: dict[str, type[Any]] = {
    "manifest.json": ManifestDocument,
    "conversation.json": ConversationDocument,
    "metadata.json": MetadataDocument,
    "summary.json": SummaryDocument,
    "search-index.json": SearchIndexDocument,
    "statistics.json": StatisticsDocument,
    "rag/chunks.json": RagChunksDocument,
    "rag/documents.json": RagDocumentsDocument,
    "rag/keywords.json": RagKeywordsDocument,
    "rag/chunk-map.json": ChunkMapDocument,
}

_EXPECTED_FILE_MAPPING = {
    "conversation": "conversation.json",
    "markdown": "conversation.md",
    "metadata": "metadata.json",
    "summary": "summary.json",
    "searchIndex": "search-index.json",
    "statistics": "statistics.json",
}
_EXPECTED_FOLDER_MAPPING = {"assets": "assets/", "rag": "rag/", "logs": "logs/"}


class ArchiveValidator:
    """Verify a generated archive without modifying it."""

    def validate(self, archive_root: Path, *, verify_hashes: bool = True) -> ArchiveValidationResult:
        """Run deterministic release-grade checks against one archive folder."""
        root = archive_root.expanduser().resolve()
        errors: list[str] = []
        warnings: list[str] = []
        checked_files = 0
        if not root.is_dir():
            return ArchiveValidationResult(is_valid=False, errors=[f"Archive directory does not exist: {root}"])

        for relative in REQUIRED_ARCHIVE_DIRECTORIES:
            if not (root / relative).is_dir():
                errors.append(f"Missing required directory: {relative}")
        for relative in REQUIRED_ARCHIVE_FILES:
            if not (root / relative).is_file():
                errors.append(f"Missing required file: {relative}")
            else:
                checked_files += 1

        documents = self._validate_json_documents(root, errors)
        manifest = documents.get("manifest.json")
        conversation = documents.get("conversation.json")
        if isinstance(conversation, ConversationDocument):
            self._validate_messages(
                root,
                conversation,
                errors,
                warnings,
                require_messages=conversation.version == APPLICATION_VERSION,
            )
            self._validate_markdown(root, conversation, errors)
        self._validate_document_consistency(documents, errors)
        if isinstance(manifest, ManifestDocument) and verify_hashes:
            self._validate_hashes(root, manifest, errors)

        result = ArchiveValidationResult(
            is_valid=not errors,
            errors=errors,
            warnings=warnings,
            checked_files=checked_files,
            details=self._validation_details(documents, checked_files, verify_hashes),
        )
        if errors:
            LOGGER.error("Archive validation failed for %s: %s", root, errors)
        else:
            LOGGER.info("Archive validation passed for %s", root)
        return result

    @staticmethod
    def _validate_json_documents(root: Path, errors: list[str]) -> dict[str, Any]:
        documents: dict[str, Any] = {}
        for relative, model_type in _DOCUMENT_MODELS.items():
            path = root / relative
            if not path.is_file():
                continue
            try:
                document = model_type.model_validate(read_json(path))
            except (OSError, ValueError, ValidationError) as exc:
                errors.append(f"Invalid {relative}: {exc}")
                continue
            documents[relative] = document
            ArchiveValidator._validate_envelope(relative, document, errors)
        return documents

    @staticmethod
    def _validate_envelope(relative: str, document: Any, errors: list[str]) -> None:
        expected = {
            "schemaVersion": (getattr(document, "schema_version", None), ARCHIVE_SCHEMA_VERSION),
            "format": (getattr(document, "format", None), ARCHIVE_FORMAT),
            "generatedBy": (getattr(document, "generated_by", None), "ContextVault"),
        }
        for field_name, (actual, required) in expected.items():
            if actual != required:
                errors.append(f"{relative} {field_name} is {actual!r}; expected {required!r}.")
        version = str(getattr(document, "version", "") or "")
        if not _is_semantic_version(version):
            errors.append(f"{relative} version is not a valid semantic version: {version!r}.")

    @staticmethod
    def _validated_file(root: Path, reference: str, errors: list[str]) -> Path | None:
        try:
            relative = validate_relative_archive_path(reference)
            target = ensure_within_root(root / relative, root)
        except ValueError as exc:
            errors.append(str(exc))
            return None
        if not target.is_file():
            errors.append(f"Missing referenced asset: {relative}")
            return None
        return target

    @classmethod
    def _validate_messages(
        cls,
        root: Path,
        conversation: ConversationDocument,
        errors: list[str],
        warnings: list[str],
        *,
        require_messages: bool,
    ) -> None:
        messages = conversation.data.messages
        identifiers: set[str] = set()
        reference_ids: set[str] = set()
        for index, message in enumerate(messages):
            expected_sequence = index + 1
            expected_parent = messages[index - 1].message_id if index else None
            expected_child = messages[index + 1].message_id if index + 1 < len(messages) else None
            if message.sequence_number != expected_sequence:
                errors.append(
                    f"Message {message.message_id} sequence is {message.sequence_number}; expected {expected_sequence}."
                )
            if message.message_id in identifiers:
                errors.append(f"Duplicate message ID: {message.message_id}")
            identifiers.add(message.message_id)
            if message.parent_message_id != expected_parent:
                errors.append(f"Message {message.message_id} parentMessageId does not match message order.")
            if message.child_message_id != expected_child:
                errors.append(f"Message {message.message_id} childMessageId does not match message order.")
            if message.capture_status == "skipped":
                detail = message.capture_error or "capture retries were exhausted"
                warnings.append(
                    f"Message {message.message_id} contains degraded content preserved after capture retries: {detail}"
                )

            expected_counts = {
                "characterCount": (message.character_count, len(message.plain_text)),
                "wordCount": (message.word_count, word_count(message.plain_text)),
                "estimatedTokens": (message.estimated_tokens, estimated_tokens(message.plain_text)),
            }
            for field_name, (actual, expected) in expected_counts.items():
                if actual != expected:
                    errors.append(f"Message {message.message_id} {field_name} is {actual}; expected {expected}.")

            for reference in [
                *message.code_references,
                *message.image_references,
                *message.attachment_references,
                *message.table_references,
                *message.citation_references,
            ]:
                if reference.id in reference_ids:
                    errors.append(f"Duplicate reference ID: {reference.id}")
                reference_ids.add(reference.id)

            for code in message.code_references:
                if code.character_count != len(code.raw_code):
                    errors.append(f"Code reference {code.id} characterCount does not match rawCode.")
                if code.line_count != len(code.raw_code.splitlines()):
                    errors.append(f"Code reference {code.id} lineCount does not match rawCode.")
                if code.file_path:
                    target = cls._validated_file(root, code.file_path, errors)
                    if target is not None:
                        if target.read_bytes() != code.raw_code.encode("utf-8"):
                            errors.append(f"Code reference {code.id} file content does not match rawCode.")

            for asset in [*message.image_references, *message.attachment_references]:
                if not asset.file_path:
                    continue
                target = cls._validated_file(root, asset.file_path, errors)
                if target is None:
                    continue
                data = target.read_bytes()
                if asset.file_size is None or asset.file_size != len(data):
                    errors.append(f"Asset reference {asset.id} fileSize does not match {asset.file_path}.")
                digest = hashlib.sha256(data).hexdigest()
                if not asset.sha256 or asset.sha256 != digest:
                    errors.append(f"Asset reference {asset.id} sha256 does not match {asset.file_path}.")

            for table in message.table_references:
                paths_and_expected = (
                    (table.json_file_path, None),
                    (table.html_file_path, table.html),
                    (table.markdown_file_path, table.markdown),
                )
                for reference, expected_text in paths_and_expected:
                    if not reference:
                        continue
                    target = cls._validated_file(root, reference, errors)
                    if target is None:
                        continue
                    if expected_text is not None:
                        try:
                            actual_text = target.read_text(encoding="utf-8")
                            if actual_text.rstrip("\n") != expected_text.rstrip("\n"):
                                errors.append(f"Table reference {table.id} content does not match {reference}.")
                        except UnicodeError:
                            errors.append(f"Table reference {table.id} is not valid UTF-8: {reference}")
                    else:
                        try:
                            payload = read_json(target)
                        except (OSError, ValueError) as exc:
                            errors.append(f"Invalid table JSON {reference}: {exc}")
                        else:
                            data = payload.get("data") if isinstance(payload, dict) else None
                            if data != {"headers": table.headers, "rows": table.rows}:
                                errors.append(f"Table reference {table.id} JSON does not match structured rows.")

            for citation in message.citation_references:
                if citation.file_path:
                    cls._validated_file(root, citation.file_path, errors)
        if not messages:
            if require_messages:
                errors.append("Conversation contains no messages; v0.2.0 exports cannot be partial or empty.")
            else:
                warnings.append("Conversation contains no messages.")

    @staticmethod
    def _validate_markdown(root: Path, conversation: ConversationDocument, errors: list[str]) -> None:
        markdown_path = root / "conversation.md"
        if not markdown_path.is_file():
            return
        try:
            rendered = markdown_path.read_text(encoding="utf-8")
        except UnicodeError:
            errors.append("conversation.md is not valid UTF-8.")
            return
        if not rendered.startswith(f"# {conversation.data.title}\n"):
            errors.append("conversation.md title does not match conversation.json.")
        if f"Source: {conversation.data.url}" not in rendered:
            errors.append("conversation.md source URL does not match conversation.json.")
        for message in conversation.data.messages:
            heading = f"## {message.role.title()} — Message {message.sequence_number}"
            if heading not in rendered:
                errors.append(f"conversation.md is missing message heading {message.sequence_number}.")

    @staticmethod
    def _validate_document_consistency(documents: dict[str, Any], errors: list[str]) -> None:
        conversation = documents.get("conversation.json")
        if not isinstance(conversation, ConversationDocument):
            return
        messages = conversation.data.messages
        message_ids = [message.message_id for message in messages]
        message_id_set = set(message_ids)
        user_messages = sum(message.role == "user" for message in messages)
        assistant_messages = sum(message.role == "assistant" for message in messages)

        envelope_versions = {
            relative: document.version
            for relative, document in documents.items()
            if hasattr(document, "version")
        }
        distinct_versions = set(envelope_versions.values())
        if len(distinct_versions) > 1:
            errors.append(f"Archive JSON envelope versions are inconsistent: {envelope_versions}")
        envelope_version = conversation.version

        manifest = documents.get("manifest.json")
        if isinstance(manifest, ManifestDocument):
            comparisons = {
                "conversationId": (manifest.data.conversation_id, conversation.data.conversation_id),
                "conversationTitle": (manifest.data.conversation_title, conversation.data.title),
                "archiveVersion": (manifest.data.archive_version, envelope_version),
                "archiveFormatVersion": (manifest.data.archive_format_version, ARCHIVE_SCHEMA_VERSION),
            }
            for field_name, (actual, expected) in comparisons.items():
                if actual != expected:
                    errors.append(f"manifest.json {field_name} does not match the frozen archive contract.")
            if manifest.data.file_mapping != _EXPECTED_FILE_MAPPING:
                errors.append("manifest.json fileMapping does not match the frozen archive mapping.")
            if manifest.data.folder_mapping != _EXPECTED_FOLDER_MAPPING:
                errors.append("manifest.json folderMapping does not match the frozen archive mapping.")

        metadata = documents.get("metadata.json")
        if isinstance(metadata, MetadataDocument):
            comparisons = {
                "conversationId": (metadata.data.conversation_id, conversation.data.conversation_id),
                "conversationTitle": (metadata.data.conversation_title, conversation.data.title),
                "conversationUrl": (metadata.data.conversation_url, conversation.data.url),
                "platformName": (metadata.data.platform_name, conversation.data.platform_name),
                "createdDate": (metadata.data.created_date, conversation.data.created_at),
                "totalMessages": (metadata.data.total_messages, len(messages)),
                "userMessages": (metadata.data.user_messages, user_messages),
                "assistantMessages": (metadata.data.assistant_messages, assistant_messages),
                "characterCount": (metadata.data.character_count, sum(len(message.plain_text) for message in messages)),
                "wordCount": (metadata.data.word_count, sum(word_count(message.plain_text) for message in messages)),
                "estimatedTokenCount": (
                    metadata.data.estimated_token_count,
                    sum(estimated_tokens(message.plain_text) for message in messages),
                ),
            }
            for field_name, (actual, expected) in comparisons.items():
                if actual != expected:
                    errors.append(f"metadata.json {field_name} does not match conversation.json.")
            if metadata.version == APPLICATION_VERSION:
                ArchiveValidator._validate_current_metadata(metadata, conversation, errors)

        statistics = documents.get("statistics.json")
        if isinstance(statistics, StatisticsDocument):
            expected_statistics = {
                "totalMessages": (statistics.data.total_messages, len(messages)),
                "userMessages": (statistics.data.user_messages, user_messages),
                "assistantMessages": (statistics.data.assistant_messages, assistant_messages),
                "images": (statistics.data.images, sum(len(message.image_references) for message in messages)),
                "attachments": (statistics.data.attachments, sum(len(message.attachment_references) for message in messages)),
                "codeBlocks": (statistics.data.code_blocks, sum(len(message.code_references) for message in messages)),
                "tables": (statistics.data.tables, sum(len(message.table_references) for message in messages)),
                "citations": (statistics.data.citations, sum(len(message.citation_references) for message in messages)),
                "totalCharacters": (statistics.data.total_characters, sum(len(message.plain_text) for message in messages)),
                "totalWords": (statistics.data.total_words, sum(word_count(message.plain_text) for message in messages)),
                "estimatedTokens": (
                    statistics.data.estimated_tokens,
                    sum(estimated_tokens(message.plain_text) for message in messages),
                ),
            }
            for field_name, (actual, expected) in expected_statistics.items():
                if actual != expected:
                    errors.append(f"statistics.json {field_name} does not match conversation.json.")

        search_document = documents.get("search-index.json")
        if isinstance(search_document, SearchIndexDocument):
            expected_mapping = {conversation.data.conversation_id: message_ids}
            if search_document.data.conversation_mapping != expected_mapping:
                errors.append("search-index.json conversationMapping does not match conversation.json.")
            expected_terms = search_document.data.keywords
            actual_terms = [item.term for item in search_document.data.message_mapping]
            if actual_terms != expected_terms:
                errors.append("search-index.json messageMapping terms do not preserve keyword order.")
            for mapping in search_document.data.message_mapping:
                unknown = set(mapping.message_ids) - message_id_set
                if unknown:
                    errors.append(
                        f"search-index.json term {mapping.term!r} references unknown message IDs: {sorted(unknown)}"
                    )
            for entity, mapped_ids in search_document.data.entity_mapping.items():
                unknown = set(mapped_ids) - message_id_set
                if unknown:
                    errors.append(f"search-index.json entity {entity!r} references unknown message IDs: {sorted(unknown)}")

        chunks_document = documents.get("rag/chunks.json")
        documents_document = documents.get("rag/documents.json")
        keywords_document = documents.get("rag/keywords.json")
        chunk_map_document = documents.get("rag/chunk-map.json")
        conversation_id = conversation.data.conversation_id
        for relative, document in (
            ("rag/chunks.json", chunks_document),
            ("rag/keywords.json", keywords_document),
            ("rag/chunk-map.json", chunk_map_document),
        ):
            if document is not None and document.data.conversation_id != conversation_id:
                errors.append(f"{relative} conversationId does not match conversation.json.")

        if isinstance(keywords_document, RagKeywordsDocument) and isinstance(search_document, SearchIndexDocument):
            if keywords_document.data.keywords != search_document.data.keywords:
                errors.append("rag/keywords.json keywords do not match search-index.json.")
            if keywords_document.data.topics != search_document.data.topics:
                errors.append("rag/keywords.json topics do not match search-index.json.")

        if isinstance(chunks_document, RagChunksDocument):
            chunk_ids = [chunk.chunk_id for chunk in chunks_document.data.chunks]
            if len(chunk_ids) != len(set(chunk_ids)):
                errors.append("rag/chunks.json contains duplicate chunk IDs.")
            if [chunk.sequence_number for chunk in chunks_document.data.chunks] != list(range(1, len(chunk_ids) + 1)):
                errors.append("rag/chunks.json chunk sequence numbers are not contiguous.")
            chunk_pairs = {
                (message_id, chunk.chunk_id)
                for chunk in chunks_document.data.chunks
                for message_id in chunk.message_ids
            }
            chunk_message_ids = [message_id for chunk in chunks_document.data.chunks for message_id in chunk.message_ids]
            if chunk_message_ids != message_ids:
                errors.append("rag/chunks.json does not preserve the complete conversation message order.")
            if not set(chunk_message_ids).issubset(message_id_set):
                errors.append("rag/chunks.json references unknown message IDs.")
            for chunk in chunks_document.data.chunks:
                if chunk.character_count != len(chunk.text):
                    errors.append(f"RAG chunk {chunk.chunk_id} characterCount does not match text.")
                if chunk.word_count != word_count(chunk.text):
                    errors.append(f"RAG chunk {chunk.chunk_id} wordCount does not match text.")
                if chunk.metadata.get("conversationId") != conversation_id:
                    errors.append(f"RAG chunk {chunk.chunk_id} metadata conversationId does not match.")

            if isinstance(chunk_map_document, ChunkMapDocument):
                map_pairs = {(item.message_id, item.chunk_id) for item in chunk_map_document.data.mappings}
                if map_pairs != chunk_pairs or len(chunk_map_document.data.mappings) != len(chunk_pairs):
                    errors.append("rag/chunk-map.json does not exactly match rag/chunks.json.")

            if isinstance(documents_document, RagDocumentsDocument):
                entries = documents_document.data.documents
                if len(entries) != 1:
                    errors.append("rag/documents.json must contain exactly one conversation document.")
                elif (
                    entries[0].conversation_id != conversation_id
                    or entries[0].title != conversation.data.title
                    or entries[0].source_url != conversation.data.url
                    or entries[0].chunk_ids != chunk_ids
                    or entries[0].metadata.get("messageCount") != len(messages)
                ):
                    errors.append("rag/documents.json does not match conversation.json and rag/chunks.json.")

    @staticmethod
    def _validate_current_metadata(
        metadata: MetadataDocument,
        conversation: ConversationDocument,
        errors: list[str],
    ) -> None:
        data = metadata.data
        try:
            UUID(data.export_uuid)
        except (ValueError, TypeError, AttributeError):
            errors.append("metadata.json exportUuid is missing or invalid.")
        for field_name, value in (
            ("exportTimestampUtc", data.export_timestamp_utc),
            ("exportTimestampLocal", data.export_timestamp_local),
        ):
            if value is None or value.tzinfo is None:
                errors.append(f"metadata.json {field_name} must be timezone-aware.")
        if data.export_timestamp_utc is not None and data.export_date != data.export_timestamp_utc:
            errors.append("metadata.json exportDate does not match exportTimestampUtc.")
        expected_values = {
            "contextvaultVersion": (data.contextvault_version, metadata.version),
            "exportEngineVersion": (data.export_engine_version, APPLICATION_VERSION),
            "schemaVersion": (data.schema_version, metadata.schema_version),
        }
        for field_name, (actual, expected) in expected_values.items():
            if actual != expected:
                errors.append(f"metadata.json {field_name} is {actual!r}; expected {expected!r}.")
        for field_name, value in (
            ("browserName", data.browser_name),
            ("browserVersion", data.browser_version),
            ("browserProfile", data.browser_profile),
        ):
            if not value.strip() or value.strip().casefold() == "unavailable":
                errors.append(f"metadata.json {field_name} is incomplete.")
        if data.estimated_size <= 0:
            errors.append("metadata.json estimatedSize must be greater than zero.")
        messages = conversation.data.messages
        expected_counts = {
            "images": (data.images, sum(len(item.image_references) for item in messages)),
            "attachments": (data.attachments, sum(len(item.attachment_references) for item in messages)),
            "codeBlocks": (data.code_blocks, sum(len(item.code_references) for item in messages)),
            "tables": (data.tables, sum(len(item.table_references) for item in messages)),
        }
        for field_name, (actual, expected) in expected_counts.items():
            if actual != expected:
                errors.append(f"metadata.json {field_name} is {actual}; expected {expected}.")

    @staticmethod
    def _validation_details(
        documents: dict[str, Any],
        checked_files: int,
        verify_hashes: bool,
    ) -> dict[str, Any]:
        details: dict[str, Any] = {
            "checkedFiles": checked_files,
            "hashVerification": "enabled" if verify_hashes else "deferred",
        }
        metadata = documents.get("metadata.json")
        if isinstance(metadata, MetadataDocument):
            details["metadata"] = {
                "archiveVersion": metadata.version,
                "conversationId": metadata.data.conversation_id,
                "exportUuid": metadata.data.export_uuid or "legacy",
                "browser": metadata.data.browser_name,
                "browserVersion": metadata.data.browser_version,
                "estimatedSize": metadata.data.estimated_size,
            }
        statistics = documents.get("statistics.json")
        if isinstance(statistics, StatisticsDocument):
            details["statistics"] = {
                "messages": statistics.data.total_messages,
                "images": statistics.data.images,
                "attachments": statistics.data.attachments,
                "codeBlocks": statistics.data.code_blocks,
                "tables": statistics.data.tables,
                "characters": statistics.data.total_characters,
            }
        return details

    @staticmethod
    def _validate_hashes(root: Path, manifest: ManifestDocument, errors: list[str]) -> None:
        expected_paths = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
            and path.relative_to(root).as_posix() != "manifest.json"
            and not path.relative_to(root).as_posix().startswith("logs/")
        }
        declared_paths: list[str] = []
        for entry in manifest.data.hash_information:
            try:
                relative = validate_relative_archive_path(entry.path)
                target = ensure_within_root(root / relative, root)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            declared_paths.append(relative)
            if not target.is_file():
                errors.append(f"Hashed file is missing: {relative}")
                continue
            data = target.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry.sha256:
                errors.append(f"SHA256 mismatch: {relative}")
            if len(data) != entry.size:
                errors.append(f"Size mismatch: {relative}")

        duplicates = sorted(path for path, count in Counter(declared_paths).items() if count > 1)
        if duplicates:
            errors.append(f"Manifest contains duplicate hash entries: {duplicates}")
        missing = sorted(expected_paths - set(declared_paths))
        if missing:
            errors.append(f"Manifest is missing hash entries: {missing}")
        unexpected = sorted(set(declared_paths) - expected_paths)
        if unexpected:
            errors.append(f"Manifest contains unexpected hash entries: {unexpected}")


_SEMANTIC_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


def _is_semantic_version(value: str) -> bool:
    return bool(_SEMANTIC_VERSION_PATTERN.fullmatch(value))
