"""Structured, queue-backed application logging."""

from __future__ import annotations

import logging
import logging.handlers
import queue
from pathlib import Path

from src.utils.paths import log_directory


class UiLogHandler(logging.Handler):
    """Forward formatted log lines to a thread-safe UI queue."""

    def __init__(self, output_queue: queue.Queue[str]) -> None:
        super().__init__()
        self._output_queue = output_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._output_queue.put_nowait(self.format(record))
        except (queue.Full, ValueError):
            return


class LoggingService:
    """Own the application's QueueHandler and QueueListener lifecycle."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or log_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.ui_queue: queue.Queue[str] = queue.Queue(maxsize=5000)
        self._record_queue: queue.Queue[logging.LogRecord] = queue.Queue()
        self._listener: logging.handlers.QueueListener | None = None
        self._configured = False

    def configure(self, level: int = logging.INFO) -> None:
        """Configure root logging exactly once."""
        if self._configured:
            return
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.handlers.RotatingFileHandler(
            self.directory / "contextvault.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        ui_handler = UiLogHandler(self.ui_queue)
        ui_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(level)
        queue_handler = logging.handlers.QueueHandler(self._record_queue)
        root_logger.addHandler(queue_handler)
        self._listener = logging.handlers.QueueListener(
            self._record_queue,
            file_handler,
            ui_handler,
            respect_handler_level=True,
        )
        self._listener.start()
        self._configured = True
        logging.getLogger(__name__).info("Logging initialized")

    def shutdown(self) -> None:
        """Flush queued log records and stop the listener."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        logging.shutdown()
        self._configured = False
