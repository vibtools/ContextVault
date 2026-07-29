"""Application bootstrapping and lifecycle."""

from __future__ import annotations

import logging

from src.controllers.application_controller import ApplicationController
from src.services.config_service import ConfigService
from src.services.history_service import HistoryService
from src.services.logging_service import LoggingService
from src.ui.main_window import MainWindow
from src.ui.theme import configure_theme

LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Initialize dependencies, run the UI, and release resources cleanly."""
    logging_service = LoggingService()
    logging_service.configure()
    controller: ApplicationController | None = None
    try:
        configure_theme()
        controller = ApplicationController(ConfigService(), HistoryService())
        window = MainWindow(controller, logging_service)
        LOGGER.info("ContextVault application started")
        window.mainloop()
        return 0
    except Exception:
        LOGGER.exception("ContextVault failed to start")
        return 1
    finally:
        if controller is not None:
            try:
                controller.shutdown()
            except Exception:
                LOGGER.exception("Controller cleanup failed")
        logging_service.shutdown()
