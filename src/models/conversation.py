"""Conversation-domain models used by parsers and exporters."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, field_validator

from src.models.base import ContextVaultModel


class CodeReference(ContextVaultModel):
    """Extracted code block and eventual archive reference."""

    id: str
    language: str = "text"
    raw_code: str
    file_path: str = ""
    character_count: int = 0
    line_count: int = 0


class ImageReference(ContextVaultModel):
    """Conversation image metadata and source information."""

    id: str
    source_url: str
    alt_text: str = ""
    file_path: str = ""
    media_type: str = ""
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    sha256: str = ""


class AttachmentReference(ContextVaultModel):
    """Attachment metadata and source information."""

    id: str
    source_url: str
    original_name: str
    file_path: str = ""
    media_type: str = ""
    file_size: int | None = None
    sha256: str = ""


class TableReference(ContextVaultModel):
    """Structured table representation."""

    id: str
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    html: str = ""
    markdown: str = ""
    json_file_path: str = ""
    html_file_path: str = ""
    markdown_file_path: str = ""


class CitationReference(ContextVaultModel):
    """Citation or external reference discovered in a message."""

    id: str
    url: str
    label: str = ""
    file_path: str = ""


class ConversationMessage(ContextVaultModel):
    """Self-contained lossless conversation message."""

    message_id: str
    parent_message_id: str | None = None
    child_message_id: str | None = None
    sequence_number: int = Field(ge=1)
    role: Literal["user", "assistant", "system", "tool", "unknown"] = "unknown"
    plain_text: str = ""
    markdown: str = ""
    html: str = ""
    code_references: list[CodeReference] = Field(default_factory=list)
    image_references: list[ImageReference] = Field(default_factory=list)
    attachment_references: list[AttachmentReference] = Field(default_factory=list)
    table_references: list[TableReference] = Field(default_factory=list)
    citation_references: list[CitationReference] = Field(default_factory=list)
    timestamp: datetime | None = None
    captured_at: datetime | None = None
    timestamp_source: Literal["message_timestamp", "page_state", "dom_inferred", "unknown"] = "unknown"
    capture_status: Literal["verified", "skipped"] = "verified"
    capture_attempts: int = Field(default=1, ge=1)
    capture_error: str | None = None
    source_key: str = ""
    source_signature: str = ""
    character_count: int = 0
    word_count: int = 0
    estimated_tokens: int = 0

    @field_validator("character_count", "word_count", "estimated_tokens")
    @classmethod
    def validate_non_negative_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Message counts cannot be negative.")
        return value


class ConversationRecord(ContextVaultModel):
    """Conversation metadata and ordered message collection."""

    conversation_id: str
    title: str
    url: str
    platform_name: str = "ChatGPT"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    exported_at: datetime
    exported_at_local: datetime | None = None
    export_id: str = Field(default_factory=lambda: str(uuid4()))
    timezone: str = "unknown"
    timestamp_source: Literal["message_timestamp", "page_state", "dom_inferred", "unknown"] = "unknown"
    duration_seconds: int | None = Field(default=None, ge=0)
    language: str = "unknown"
    browser_name: str = "unavailable"
    browser_version: str = "unavailable"
    browser_profile: str = "unavailable"
    chatgpt_workspace: str | None = None
    chatgpt_model: str | None = None
    estimated_size: int = Field(default=0, ge=0)
    source_message_count: int | None = Field(default=None, ge=0)
    source_asset_counts: dict[str, int] = Field(default_factory=dict)
    readiness: dict[str, Any] = Field(default_factory=dict)
    skipped_message_count: int = Field(default=0, ge=0)
    capture_warnings: list[str] = Field(default_factory=list)
    messages: list[ConversationMessage] = Field(default_factory=list)


class ConversationListItem(ContextVaultModel):
    """Lightweight sidebar conversation descriptor."""

    conversation_id: str
    title: str
    url: str
    message_count: int | None = None
    image_count: int | None = None
    code_count: int | None = None
    attachment_count: int | None = None
    estimated_size: int | None = None
