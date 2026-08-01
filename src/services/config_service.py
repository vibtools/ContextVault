"""Validated persistent settings management."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError

from src.config.constants import DEFAULT_CONFIG_FILENAME
from src.models.settings import ApplicationSettings
from src.utils.json_io import read_json, write_json
from src.utils.paths import (
    configuration_path,
    data_directory,
    portable_runtime_missing_paths,
)

LOGGER = logging.getLogger(__name__)


class ConfigService:
    """Load and atomically persist application settings."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_directory() / DEFAULT_CONFIG_FILENAME

    def load(self) -> ApplicationSettings:
        """Load settings, recovering to defaults when the file is absent or invalid."""
        if not self.path.exists():
            settings = self._default_settings()
            self.save(settings)
            return settings
        try:
            return ApplicationSettings.model_validate(read_json(self.path))
        except (OSError, ValueError, ValidationError) as exc:
            backup = self.path.with_suffix(self.path.suffix + ".invalid")
            try:
                self.path.replace(backup)
            except OSError:
                LOGGER.exception("Failed to preserve invalid settings file")
            LOGGER.error("Invalid settings recovered to defaults: %s", exc)
            settings = self._default_settings()
            self.save(settings)
            return settings

    @staticmethod
    def _default_settings() -> ApplicationSettings:
        """Load the shipped canonical defaults, with model defaults as a safe fallback."""
        defaults_path = configuration_path("defaults.json")
        try:
            return ApplicationSettings.model_validate(read_json(defaults_path))
        except (OSError, ValueError, ValidationError) as exc:
            missing_runtime = portable_runtime_missing_paths()
            LOGGER.warning(
                "Shipped defaults are unavailable or invalid at %s; using embedded safe "
                "model defaults. Keep ContextVault.exe beside the complete runtime folder. "
                "missingRuntime=%s; error=%s",
                defaults_path,
                list(missing_runtime),
                exc,
            )
            return ApplicationSettings()

    def save(self, settings: ApplicationSettings) -> None:
        """Validate and atomically persist settings."""
        validated = ApplicationSettings.model_validate(settings.model_dump())
        write_json(self.path, validated)
        LOGGER.info("Settings saved to %s", self.path)
