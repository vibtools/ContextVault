from __future__ import annotations

import threading
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

    def test_done_callback_runs_for_a_task_cancelled_while_queued(self) -> None:
        manager = TaskManager(1)
        release = threading.Event()
        started = [threading.Event(), threading.Event()]

        def blocking(index: int):
            def work(_context):
                started[index].set()
                if not release.wait(timeout=3):
                    raise TimeoutError("Test blocker was not released.")
            return work

        try:
            manager.submit("block-1", blocking(0))
            manager.submit("block-2", blocking(1))
            self.assertTrue(started[0].wait(timeout=2))
            self.assertTrue(started[1].wait(timeout=2))

            queued = manager.submit("queued", lambda _context: None)
            callback_called = threading.Event()
            self.assertTrue(manager.add_done_callback(queued, callback_called.set))
            self.assertTrue(manager.cancel(queued))
            self.assertTrue(callback_called.wait(timeout=2))
            self.assertEqual(manager.snapshot(queued).state, TaskState.CANCELLED)
        finally:
            release.set()
            manager.shutdown()


if __name__ == "__main__":
    unittest.main()
