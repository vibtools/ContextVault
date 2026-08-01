from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path
from typing import Any, Callable

from src.controllers.application_controller import ApplicationController
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
    def append(self, _record: dict[str, Any]) -> None:
        return None

    def list_records(self) -> list[dict[str, Any]]:
        return []


class _FailingExportPipeline:
    def export_conversation(
        self,
        _context: Any,
        _item: ConversationListItem,
        _settings: ApplicationSettings,
        _destination: Path,
    ) -> dict[str, Any]:
        raise RuntimeError("simulated export failure")


class _BlockingExportPipeline:
    def __init__(self, *, initially_released: bool = False) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        if initially_released:
            self.release.set()

    def export_conversation(
        self,
        _context: Any,
        item: ConversationListItem,
        _settings: ApplicationSettings,
        destination: Path,
    ) -> dict[str, Any]:
        self.started.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("Test export release was not signalled.")
        return {
            "archivePath": str(destination / item.title),
            "zipPath": "",
            "conversationId": item.conversation_id,
            "title": item.title,
            "messageCount": 1,
            "validation": {"isValid": True},
        }


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
        time.sleep(0.005)


class BrowserWorkflowLifecycleRegressionTests(unittest.TestCase):
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
            conversationId="lease-regression-id",
            title="Lease Regression",
            url="https://chatgpt.com/c/lease-regression-id",
        )

    def tearDown(self) -> None:
        self.controller.shutdown()
        self.temporary.cleanup()

    def test_terminal_failure_releases_lease_before_done_callback_runs(self) -> None:
        delayed_callbacks: list[Callable[[], None]] = []

        def delay_done_callback(task_id: str, callback: Callable[[], None]) -> bool:
            self.assertIsNotNone(self.controller.task_manager.snapshot(task_id))
            delayed_callbacks.append(callback)
            return True

        self.controller.task_manager.add_done_callback = delay_done_callback  # type: ignore[method-assign]
        self.controller.export_pipeline = _FailingExportPipeline()  # type: ignore[assignment]

        first = self.controller.export_conversations([self.item])
        self.assertEqual(_wait_for_terminal(self.controller, first), TaskState.FAILED)
        self.assertEqual(self.controller._browser_workflow_gate.active_workflow, "")
        self.assertEqual(len(delayed_callbacks), 1)

        replacement = _BlockingExportPipeline(initially_released=True)
        self.controller.export_pipeline = replacement  # type: ignore[assignment]
        second = self.controller.export_conversations([self.item])
        self.assertEqual(_wait_for_terminal(self.controller, second), TaskState.COMPLETED)

    def test_late_callback_for_old_lease_cannot_release_new_owner(self) -> None:
        delayed_callbacks: list[Callable[[], None]] = []

        def delay_done_callback(_task_id: str, callback: Callable[[], None]) -> bool:
            delayed_callbacks.append(callback)
            return True

        self.controller.task_manager.add_done_callback = delay_done_callback  # type: ignore[method-assign]
        self.controller.export_pipeline = _FailingExportPipeline()  # type: ignore[assignment]
        first = self.controller.export_conversations([self.item])
        self.assertEqual(_wait_for_terminal(self.controller, first), TaskState.FAILED)

        blocking = _BlockingExportPipeline()
        self.controller.export_pipeline = blocking  # type: ignore[assignment]
        second = self.controller.export_conversations([self.item])
        self.assertTrue(blocking.started.wait(timeout=3))
        self.assertEqual(
            self.controller._browser_workflow_gate.active_workflow,
            "Export conversations",
        )

        delayed_callbacks[0]()
        self.assertEqual(
            self.controller._browser_workflow_gate.active_workflow,
            "Export conversations",
        )
        with self.assertRaisesRegex(RuntimeError, "already using the managed browser"):
            self.controller.export_conversations([self.item])

        blocking.release.set()
        self.assertEqual(_wait_for_terminal(self.controller, second), TaskState.COMPLETED)


if __name__ == "__main__":
    unittest.main()
