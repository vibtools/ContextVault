from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path
from typing import Any

from src.controllers.application_controller import (
    ApplicationController,
    _deduplicate_conversations,
)
from src.core.export_pipeline import _resolved_conversation_title
from src.models.conversation import ConversationListItem
from src.models.settings import ApplicationSettings
from src.models.tasks import TaskState


class _ConfigService:
    def __init__(self, settings: ApplicationSettings) -> None:
        self._settings = settings

    def load(self) -> ApplicationSettings:
        return self._settings

    def save(self, settings: ApplicationSettings) -> None:
        self._settings = settings


class _HistoryService:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(self, record: dict[str, Any]) -> None:
        self.records.append(dict(record))

    def list_records(self) -> list[dict[str, Any]]:
        return list(reversed(self.records))


class _BlockingExportPipeline:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls: list[ConversationListItem] = []

    def export_conversation(
        self,
        _context: Any,
        item: ConversationListItem,
        _settings: ApplicationSettings,
        destination: Path,
    ) -> dict[str, Any]:
        self.calls.append(item)
        self.started.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("Test export release was not signalled.")
        archive = destination / item.title
        return {
            "archivePath": str(archive),
            "zipPath": "",
            "conversationId": item.conversation_id,
            "title": item.title,
            "messageCount": 1,
            "validation": {"isValid": True},
        }


class _FailingExportPipeline:
    def export_conversation(
        self,
        _context: Any,
        _item: ConversationListItem,
        _settings: ApplicationSettings,
        _destination: Path,
    ) -> dict[str, Any]:
        raise RuntimeError("simulated export failure")


def _wait_for_terminal(controller: ApplicationController, task_id: str) -> TaskState:
    deadline = time.monotonic() + 5
    while True:
        snapshot = controller.task_manager.snapshot(task_id)
        if snapshot is not None and snapshot.state in {
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.CANCELLED,
        }:
            return snapshot.state
        if time.monotonic() >= deadline:
            raise AssertionError("Task did not reach a terminal state.")
        time.sleep(0.01)


class ExportWorkflowExclusivityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = __import__("tempfile").TemporaryDirectory()
        settings = ApplicationSettings.model_validate(
            {
                "export": {
                    "defaultFolder": self.temporary.name,
                    "archiveName": "{title}",
                }
            }
        )
        self.controller = ApplicationController(
            _ConfigService(settings),  # type: ignore[arg-type]
            _HistoryService(),  # type: ignore[arg-type]
        )
        self.item = ConversationListItem(
            conversationId="6a5e3c13-f558-83e9-8419-69886adcb4b0",
            title="Canonical Chat Title",
            url="https://chatgpt.com/c/6a5e3c13-f558-83e9-8419-69886adcb4b0",
        )

    def tearDown(self) -> None:
        self.controller.shutdown()
        self.temporary.cleanup()

    def test_duplicate_export_submission_is_rejected_before_browser_interleaving(self) -> None:
        pipeline = _BlockingExportPipeline()
        self.controller.export_pipeline = pipeline  # type: ignore[assignment]

        task_id = self.controller.export_conversations([self.item])
        self.assertTrue(pipeline.started.wait(timeout=3))

        with self.assertRaisesRegex(RuntimeError, "already using the managed browser"):
            self.controller.export_conversations([self.item])
        with self.assertRaisesRegex(RuntimeError, "already using the managed browser"):
            self.controller.scan_conversations()
        with self.assertRaisesRegex(RuntimeError, "already using the managed browser"):
            self.controller.refresh_browser()

        pipeline.release.set()
        self.assertEqual(_wait_for_terminal(self.controller, task_id), TaskState.COMPLETED)
        self.assertEqual(len(pipeline.calls), 1)

    def test_browser_workflow_lease_is_released_after_export_failure(self) -> None:
        self.controller.export_pipeline = _FailingExportPipeline()  # type: ignore[assignment]
        first = self.controller.export_conversations([self.item])
        self.assertEqual(_wait_for_terminal(self.controller, first), TaskState.FAILED)

        pipeline = _BlockingExportPipeline()
        pipeline.release.set()
        self.controller.export_pipeline = pipeline  # type: ignore[assignment]
        second = self.controller.export_conversations([self.item])
        self.assertEqual(_wait_for_terminal(self.controller, second), TaskState.COMPLETED)

    def test_cancelled_export_keeps_lease_until_the_running_workflow_stops(self) -> None:
        pipeline = _BlockingExportPipeline()
        self.controller.export_pipeline = pipeline  # type: ignore[assignment]

        task_id = self.controller.export_conversations([self.item])
        self.assertTrue(pipeline.started.wait(timeout=3))
        self.assertTrue(self.controller.cancel_export())

        with self.assertRaisesRegex(RuntimeError, "already using the managed browser"):
            self.controller.export_conversations([self.item])

        pipeline.release.set()
        self.assertEqual(_wait_for_terminal(self.controller, task_id), TaskState.CANCELLED)

        replacement = _BlockingExportPipeline()
        replacement.release.set()
        self.controller.export_pipeline = replacement  # type: ignore[assignment]
        next_task = self.controller.export_conversations([self.item])
        self.assertEqual(_wait_for_terminal(self.controller, next_task), TaskState.COMPLETED)

    def test_scanned_chat_title_is_canonical_and_message_heading_is_not_considered(self) -> None:
        self.assertEqual(
            _resolved_conversation_title(
                "YGIT 05_Project-Context&Update",
                self.item.conversation_id,
            ),
            "YGIT 05_Project-Context&Update",
        )
        self.assertEqual(
            _resolved_conversation_title("ChatGPT", self.item.conversation_id),
            "Conversation #6a5e3c13",
        )

    def test_selected_conversation_duplicates_are_removed_in_order(self) -> None:
        duplicate = ConversationListItem.model_validate(
            self.item.model_dump(mode="json", by_alias=True)
        )
        other = ConversationListItem(
            conversationId="other-id",
            title="Other",
            url="https://chatgpt.com/c/other-id",
        )

        result = _deduplicate_conversations([self.item, duplicate, other, self.item])
        self.assertEqual(
            [item.conversation_id for item in result],
            [self.item.conversation_id, "other-id"],
        )


if __name__ == "__main__":
    unittest.main()
