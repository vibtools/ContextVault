from __future__ import annotations

import time
import unittest

from src.core.task_manager import TaskManager
from src.models.tasks import TaskState


class TaskManagerTests(unittest.TestCase):
    def test_task_completion_and_snapshot(self) -> None:
        manager = TaskManager(2)
        try:
            task_id = manager.submit("value", lambda context: 42)
            deadline = time.monotonic() + 3
            snapshot = manager.snapshot(task_id)
            while snapshot is not None and snapshot.state not in {TaskState.COMPLETED, TaskState.FAILED}:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
                snapshot = manager.snapshot(task_id)
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.state, TaskState.COMPLETED)
            self.assertEqual(manager.active_count(), 0)
        finally:
            manager.shutdown()

    def test_cooperative_cancellation(self) -> None:
        manager = TaskManager(1)
        try:
            def work(context):
                while True:
                    context.check_cancelled()
                    time.sleep(0.01)
            task_id = manager.submit("cancel", work)
            time.sleep(0.05)
            self.assertTrue(manager.cancel(task_id))
            deadline = time.monotonic() + 3
            snapshot = manager.snapshot(task_id)
            while snapshot is not None and snapshot.state not in {TaskState.CANCELLED, TaskState.FAILED}:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
                snapshot = manager.snapshot(task_id)
            self.assertEqual(snapshot.state, TaskState.CANCELLED)
        finally:
            manager.shutdown()


if __name__ == "__main__":
    unittest.main()
