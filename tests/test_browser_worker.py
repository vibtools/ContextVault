from __future__ import annotations

import asyncio
import concurrent.futures
import threading
import time
import unittest
from src.browser.session_worker import BrowserSessionWorker


class _FakeBrowserManager:
    async def close(self) -> dict[str, object]:
        return {"connected": False}

    async def echo(self, value: object) -> object:
        await asyncio.sleep(0)
        return value

    async def block(self) -> None:
        await asyncio.sleep(60)

    async def interrupt(self) -> None:
        raise InterruptedError("expected cancellation")


class BrowserSessionWorkerTests(unittest.TestCase):
    def test_worker_serializes_commands_and_restarts(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            worker = BrowserSessionWorker(executor, manager_factory=_FakeBrowserManager)
            self.assertEqual(worker.submit("echo", value=42).result(timeout=2), 42)
            worker.stop(timeout=2)
            self.assertEqual(worker.submit("echo", value="restart").result(timeout=2), "restart")
            worker.stop(timeout=2)

    def test_stop_cancels_active_and_queued_commands(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            worker = BrowserSessionWorker(executor, manager_factory=_FakeBrowserManager)
            active = worker.submit("block")
            queued = worker.submit("echo", value="queued")
            time.sleep(0.05)
            worker.stop(timeout=2)
            self.assertTrue(active.cancelled())
            self.assertTrue(queued.cancelled())


    def test_expected_interruption_is_not_logged_as_browser_failure(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            worker = BrowserSessionWorker(executor, manager_factory=_FakeBrowserManager)
            with self.assertLogs("src.browser.session_worker", level="INFO") as captured:
                with self.assertRaises(InterruptedError):
                    worker.submit("interrupt").result(timeout=2)
            worker.stop(timeout=2)

        joined = "\n".join(captured.output)
        self.assertIn("Browser command cancelled: interrupt", joined)
        self.assertNotIn("Browser command failed: interrupt", joined)

    def test_concurrent_start_is_idempotent(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            worker = BrowserSessionWorker(executor, manager_factory=_FakeBrowserManager)
            threads = [threading.Thread(target=worker.start) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(worker.submit("echo", value="ok").result(timeout=2), "ok")
            worker.stop(timeout=2)


if __name__ == "__main__":
    unittest.main()
