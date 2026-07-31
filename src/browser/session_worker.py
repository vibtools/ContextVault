"""Dedicated browser command worker hosted by the centralized executor."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import queue
import threading
from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BrowserCommand:
    """One serialized browser operation and its public future."""

    name: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    future: concurrent.futures.Future[Any] = field(default_factory=concurrent.futures.Future)


class BrowserSessionWorker:
    """Keep all Playwright objects on one deterministic worker thread."""

    def __init__(
        self,
        executor: concurrent.futures.ThreadPoolExecutor,
        manager_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._executor = executor
        self._manager_factory = manager_factory
        self._commands: queue.Queue[BrowserCommand] = queue.Queue()
        self._started = threading.Event()
        self._stopped = threading.Event()
        self._runner_future: concurrent.futures.Future[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._active_task: asyncio.Task[Any] | None = None
        self._state_lock = threading.RLock()
        self._accepting = False

    def start(self) -> None:
        """Start the browser command loop once, safely across concurrent callers."""
        with self._state_lock:
            if self._runner_future is not None and not self._runner_future.done():
                return
            self._started.clear()
            self._stopped.clear()
            self._accepting = True
            self._runner_future = self._executor.submit(self._run)
        if not self._started.wait(timeout=10):
            with self._state_lock:
                self._accepting = False
            raise RuntimeError("Browser worker failed to initialize.")

    def submit(self, name: str, **kwargs: Any) -> concurrent.futures.Future[Any]:
        """Queue a supported BrowserManager async method."""
        self.start()
        command = BrowserCommand(name=name, kwargs=kwargs)
        with self._state_lock:
            if not self._accepting:
                command.future.set_exception(RuntimeError("Browser worker is shutting down."))
                return command.future
            self._commands.put(command)
        return command.future

    def stop(self, timeout: float = 20.0) -> None:
        """Cancel active work, close browser resources, and stop the worker loop."""
        with self._state_lock:
            runner = self._runner_future
            if runner is None:
                return
            self._accepting = False
            loop = self._loop
            active_task = self._active_task

        self._cancel_queued_commands()
        if loop is not None and active_task is not None and not active_task.done():
            loop.call_soon_threadsafe(active_task.cancel)
        stop_command = BrowserCommand(name="__stop__")
        self._commands.put(stop_command)
        try:
            stop_command.future.result(timeout=timeout)
            runner.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            LOGGER.error("Browser worker did not stop within %.1f seconds", timeout)
        finally:
            with self._state_lock:
                if self._runner_future is runner and runner.done():
                    self._runner_future = None
                self._loop = None
                self._active_task = None

    def _cancel_queued_commands(self) -> None:
        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return
            if command.name == "__stop__":
                continue
            command.future.cancel()

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if self._manager_factory is None:
            from src.browser.browser_manager import BrowserManager

            manager = BrowserManager()
        else:
            manager = self._manager_factory()
        with self._state_lock:
            self._loop = loop
        self._started.set()
        try:
            while True:
                command = self._commands.get()
                if command.name == "__stop__":
                    try:
                        loop.run_until_complete(manager.close())
                        if not command.future.done():
                            command.future.set_result(None)
                    except Exception as exc:
                        if not command.future.done():
                            command.future.set_exception(exc)
                    break
                if command.future.cancelled():
                    continue
                try:
                    operation = getattr(manager, command.name, None)
                    if operation is None or not callable(operation) or command.name.startswith("_"):
                        raise AttributeError(f"Unsupported browser command: {command.name}")
                    task = loop.create_task(operation(**command.kwargs))
                    with self._state_lock:
                        self._active_task = task
                    result = loop.run_until_complete(task)
                    if not command.future.done():
                        command.future.set_result(result)
                except asyncio.CancelledError:
                    command.future.cancel()
                except InterruptedError as exc:
                    LOGGER.info("Browser command cancelled: %s", command.name)
                    if not command.future.done():
                        command.future.set_exception(exc)
                except Exception as exc:
                    LOGGER.exception("Browser command failed: %s", command.name)
                    if not command.future.done():
                        command.future.set_exception(exc)
                finally:
                    with self._state_lock:
                        self._active_task = None
        finally:
            try:
                loop.run_until_complete(manager.close())
            except Exception:
                LOGGER.exception("Browser manager cleanup failed")
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
            with self._state_lock:
                self._loop = None
                self._active_task = None
                self._accepting = False
            self._stopped.set()
