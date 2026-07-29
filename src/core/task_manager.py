"""Centralized managed background task executor."""

from __future__ import annotations

import concurrent.futures
import logging
import queue
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import uuid4

from src.models.tasks import ApplicationEvent, EventType, TaskProgress, TaskSnapshot, TaskState

LOGGER = logging.getLogger(__name__)
TaskFunction = Callable[["TaskContext"], Any]


@dataclass(slots=True)
class _TaskRecord:
    task_id: str
    name: str
    state: TaskState
    created_at: datetime
    cancellation_event: threading.Event
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str = ""
    future: concurrent.futures.Future[Any] | None = None


class TaskContext:
    """Worker-owned task controls and rate-limited progress reporter."""

    def __init__(
        self,
        task_id: str,
        cancellation_event: threading.Event,
        event_queue: queue.Queue[ApplicationEvent],
    ) -> None:
        self.task_id = task_id
        self.cancellation_event = cancellation_event
        self._event_queue = event_queue
        self._last_progress_time = 0.0
        self._last_percentage = -1.0

    def check_cancelled(self) -> None:
        """Raise a cooperative cancellation exception when requested."""
        if self.cancellation_event.is_set():
            raise InterruptedError("Task cancellation requested.")

    def report_progress(
        self,
        stage: str,
        percentage: float,
        current_item: str = "",
        completed_items: int = 0,
        total_items: int = 0,
        eta_seconds: float | None = None,
        message: str = "",
        *,
        force: bool = False,
    ) -> None:
        """Publish a bounded progress event without flooding the UI queue."""
        now = time.monotonic()
        bounded = max(0.0, min(100.0, percentage))
        should_emit = force or bounded in {0.0, 100.0} or now - self._last_progress_time >= 0.1 or abs(bounded - self._last_percentage) >= 1.0
        if not should_emit:
            return
        self._last_progress_time = now
        self._last_percentage = bounded
        progress = TaskProgress(
            task_id=self.task_id,
            stage=stage,
            percentage=bounded,
            current_item=current_item,
            completed_items=completed_items,
            total_items=total_items,
            eta_seconds=eta_seconds,
            message=message,
        )
        self.emit(EventType.PROGRESS, progress.model_dump(mode="json", by_alias=True))

    def emit(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Publish an application event to the controller/UI queue."""
        event = ApplicationEvent(
            event_type=event_type,
            created_at=datetime.now(UTC),
            task_id=self.task_id,
            payload=payload,
        )
        self._event_queue.put(event)


class TaskManager:
    """Own one reusable ThreadPoolExecutor and deterministic task lifecycle."""

    def __init__(self, worker_threads: int) -> None:
        self.worker_threads = worker_threads
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(2, worker_threads + 1),
            thread_name_prefix="ContextVaultWorker",
        )
        self.events: queue.Queue[ApplicationEvent] = queue.Queue()
        self._records: dict[str, _TaskRecord] = {}
        self._lock = threading.Lock()
        self._accepting = True

    def submit(self, name: str, function: TaskFunction) -> str:
        """Queue a managed task and return its stable identifier."""
        with self._lock:
            if not self._accepting:
                raise RuntimeError("Task manager is shutting down.")
            task_id = str(uuid4())
            record = _TaskRecord(
                task_id=task_id,
                name=name,
                state=TaskState.QUEUED,
                created_at=datetime.now(UTC),
                cancellation_event=threading.Event(),
            )
            self._records[task_id] = record
            record.future = self.executor.submit(self._execute, record, function)
            return task_id

    def cancel(self, task_id: str) -> bool:
        """Request cooperative cancellation of a queued or running task."""
        with self._lock:
            record = self._records.get(task_id)
            if record is None or record.state in {TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED}:
                return False
            record.cancellation_event.set()
            if record.future is not None and record.future.cancel():
                record.state = TaskState.CANCELLED
                record.completed_at = datetime.now(UTC)
                self._emit_terminal(record, EventType.STATUS, {"state": TaskState.CANCELLED.value})
            return True

    def snapshot(self, task_id: str) -> TaskSnapshot | None:
        """Return an immutable task snapshot."""
        with self._lock:
            record = self._records.get(task_id)
            if record is None:
                return None
            return self._snapshot(record)

    def list_snapshots(self) -> list[TaskSnapshot]:
        """Return all task snapshots in creation order."""
        with self._lock:
            return [self._snapshot(record) for record in self._records.values()]

    def active_count(self) -> int:
        """Return queued/running task count."""
        with self._lock:
            return sum(record.state in {TaskState.QUEUED, TaskState.STARTED, TaskState.RUNNING} for record in self._records.values())

    def cancel_all(self) -> None:
        """Signal cooperative cancellation for every active task."""
        with self._lock:
            records = list(self._records.values())
        for record in records:
            if record.state in {TaskState.QUEUED, TaskState.STARTED, TaskState.RUNNING}:
                record.cancellation_event.set()

    def shutdown(self, timeout: float = 30.0) -> None:
        """Stop accepting work, signal cancellation, and close the executor."""
        with self._lock:
            self._accepting = False
            records = list(self._records.values())
        futures: list[concurrent.futures.Future[Any]] = []
        for record in records:
            if record.state in {TaskState.QUEUED, TaskState.STARTED, TaskState.RUNNING}:
                record.cancellation_event.set()
            if record.future is not None and not record.future.done():
                record.future.cancel()
                futures.append(record.future)
        _, unfinished = concurrent.futures.wait(futures, timeout=max(0.0, timeout)) if futures else (set(), set())
        if unfinished:
            LOGGER.warning("%s background task(s) did not stop within %.1f seconds", len(unfinished), timeout)
        self.executor.shutdown(wait=False, cancel_futures=True)
        LOGGER.info("Task manager shut down")

    def _execute(self, record: _TaskRecord, function: TaskFunction) -> Any:
        with self._lock:
            if record.cancellation_event.is_set():
                record.state = TaskState.CANCELLED
                record.completed_at = datetime.now(UTC)
                self._emit_terminal(record, EventType.STATUS, {"state": TaskState.CANCELLED.value})
                return None
            record.state = TaskState.STARTED
            record.started_at = datetime.now(UTC)
        context = TaskContext(record.task_id, record.cancellation_event, self.events)
        context.emit(EventType.STATUS, {"name": record.name, "state": TaskState.STARTED.value})
        with self._lock:
            record.state = TaskState.RUNNING
        try:
            result = function(context)
            context.check_cancelled()
        except InterruptedError as exc:
            with self._lock:
                record.state = TaskState.CANCELLED
                record.completed_at = datetime.now(UTC)
                record.error = str(exc)
            LOGGER.info("Task cancelled: %s", record.name)
            self._emit_terminal(record, EventType.STATUS, {"name": record.name, "state": TaskState.CANCELLED.value})
            return None
        except Exception as exc:
            with self._lock:
                record.state = TaskState.FAILED
                record.completed_at = datetime.now(UTC)
                record.error = str(exc)
            LOGGER.exception("Task failed: %s", record.name)
            self._emit_terminal(
                record,
                EventType.ERROR,
                {"name": record.name, "state": TaskState.FAILED.value, "message": str(exc)},
            )
            return None
        with self._lock:
            record.state = TaskState.COMPLETED
            record.completed_at = datetime.now(UTC)
        self._emit_terminal(
            record,
            EventType.COMPLETED,
            {"name": record.name, "state": TaskState.COMPLETED.value, "result": result},
        )
        return result

    def _emit_terminal(self, record: _TaskRecord, event_type: EventType, payload: dict[str, Any]) -> None:
        self.events.put(
            ApplicationEvent(
                event_type=event_type,
                created_at=datetime.now(UTC),
                task_id=record.task_id,
                payload=payload,
            )
        )

    @staticmethod
    def _snapshot(record: _TaskRecord) -> TaskSnapshot:
        return TaskSnapshot(
            task_id=record.task_id,
            name=record.name,
            state=record.state,
            created_at=record.created_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            error=record.error,
        )
