"""Background task state and progress models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from src.models.base import ContextVaultModel


class TaskState(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class EventType(StrEnum):
    PROGRESS = "progress"
    STATUS = "status"
    COMPLETED = "completed"
    ERROR = "error"
    NOTIFICATION = "notification"
    CONVERSATIONS = "conversations"
    ARCHIVES = "archives"
    ARCHIVE_PREVIEW = "archivePreview"
    HISTORY = "history"
    BROWSER = "browser"


class TaskProgress(ContextVaultModel):
    """Rate-limited worker progress message."""

    task_id: str
    stage: str
    percentage: float = Field(ge=0.0, le=100.0)
    current_item: str = ""
    completed_items: int = 0
    total_items: int = 0
    eta_seconds: float | None = None
    message: str = ""


class ApplicationEvent(ContextVaultModel):
    """Thread-safe worker-to-controller/UI event."""

    event_type: EventType
    created_at: datetime
    task_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskSnapshot(ContextVaultModel):
    """Read-only public task state."""

    task_id: str
    name: str
    state: TaskState
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str = ""
