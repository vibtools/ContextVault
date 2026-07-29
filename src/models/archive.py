"""Archive document models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from src.models.base import ContextVaultModel
from src.models.conversation import ConversationMessage


class JsonEnvelope(ContextVaultModel):
    """Common metadata required by generated JSON documents."""

    schema_version: str = "1.0"
    format: str = "contextvault"
    generated_by: str = "ContextVault"
    generated_at: datetime
    version: str = "1.0.0"


class ConversationData(ContextVaultModel):
    """Lossless conversation JSON payload."""

    conversation_id: str
    title: str
    url: str
    platform_name: str
    created_at: datetime | None = None
    messages: list[ConversationMessage]


class ConversationDocument(JsonEnvelope):
    """conversation.json document."""

    data: ConversationData


class MetadataData(ContextVaultModel):
    """metadata.json payload."""

    conversation_title: str
    conversation_url: str
    conversation_id: str
    platform_name: str
    export_date: datetime
    created_date: datetime | None = None
    language: str
    total_messages: int
    user_messages: int
    assistant_messages: int
    character_count: int
    word_count: int
    estimated_token_count: int


class MetadataDocument(JsonEnvelope):
    """metadata.json document."""

    data: MetadataData


class SummaryData(ContextVaultModel):
    """summary.json payload."""

    short_summary: str
    long_summary: str
    main_topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    important_decisions: list[str] = Field(default_factory=list)
    todo_list: list[str] = Field(default_factory=list)
    mentioned_technologies: list[str] = Field(default_factory=list)
    mentioned_libraries: list[str] = Field(default_factory=list)
    mentioned_urls: list[str] = Field(default_factory=list)
    mentioned_files: list[str] = Field(default_factory=list)


class SummaryDocument(JsonEnvelope):
    """summary.json document."""

    data: SummaryData


class SearchMessageMapping(ContextVaultModel):
    """Search-term-to-message relationship."""

    term: str
    message_ids: list[str] = Field(default_factory=list)


class SearchIndexData(ContextVaultModel):
    """search-index.json payload."""

    keywords: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    important_terms: list[str] = Field(default_factory=list)
    entity_mapping: dict[str, list[str]] = Field(default_factory=dict)
    message_mapping: list[SearchMessageMapping] = Field(default_factory=list)
    conversation_mapping: dict[str, list[str]] = Field(default_factory=dict)


class SearchIndexDocument(JsonEnvelope):
    """search-index.json document."""

    data: SearchIndexData


class StatisticsData(ContextVaultModel):
    """statistics.json payload."""

    total_messages: int
    user_messages: int
    assistant_messages: int
    images: int
    attachments: int
    code_blocks: int
    tables: int
    citations: int
    total_characters: int
    total_words: int
    estimated_tokens: int


class StatisticsDocument(JsonEnvelope):
    """statistics.json document."""

    data: StatisticsData


class FileHash(ContextVaultModel):
    """Manifest integrity entry."""

    path: str
    sha256: str
    size: int


class ValidationStatus(ContextVaultModel):
    """Archive validation outcome."""

    status: Literal["valid", "invalid", "notValidated"]
    validated_at: datetime | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ManifestData(ContextVaultModel):
    """manifest.json payload."""

    archive_id: str
    archive_version: str
    archive_format_version: str
    export_date: datetime
    conversation_id: str
    conversation_title: str
    file_mapping: dict[str, str]
    folder_mapping: dict[str, str]
    hash_information: list[FileHash]
    validation_status: ValidationStatus


class ManifestDocument(JsonEnvelope):
    """Archive entry-point document."""

    data: ManifestData


class RagChunk(ContextVaultModel):
    """Logical RAG chunk that preserves message boundaries."""

    chunk_id: str
    sequence_number: int
    message_ids: list[str]
    text: str
    character_count: int
    word_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagChunksData(ContextVaultModel):
    conversation_id: str
    chunks: list[RagChunk]


class RagChunksDocument(JsonEnvelope):
    data: RagChunksData


class RagDocumentEntry(ContextVaultModel):
    document_id: str
    conversation_id: str
    title: str
    source_url: str
    chunk_ids: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagDocumentsData(ContextVaultModel):
    documents: list[RagDocumentEntry]


class RagDocumentsDocument(JsonEnvelope):
    data: RagDocumentsData


class RagKeywordsData(ContextVaultModel):
    conversation_id: str
    keywords: list[str]
    topics: list[str]


class RagKeywordsDocument(JsonEnvelope):
    data: RagKeywordsData


class ChunkMapEntry(ContextVaultModel):
    message_id: str
    chunk_id: str


class ChunkMapData(ContextVaultModel):
    conversation_id: str
    mappings: list[ChunkMapEntry]


class ChunkMapDocument(JsonEnvelope):
    data: ChunkMapData


class ArchiveValidationResult(ContextVaultModel):
    """Detailed validator result returned to application code."""

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_files: int = 0
