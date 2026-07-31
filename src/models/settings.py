"""Persistent application settings models."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator

from src.config.constants import DEFAULT_CDP_ENDPOINT, SUPPORTED_BROWSER
from src.models.base import ContextVaultModel


class AssetSettings(ContextVaultModel):
    """Controls which archive components are generated."""

    images: bool = True
    code: bool = True
    tables: bool = True
    attachments: bool = False
    markdown: bool = True
    json_output: bool = Field(default=True, alias="json")
    summary: bool = True
    statistics: bool = True
    search_index: bool = True


class ExportSettings(ContextVaultModel):
    """Archive output behavior."""

    default_folder: str = "exports"
    archive_name: str = "{title}"
    auto_create_folder: bool = True
    overwrite: bool = False
    compress: bool = False
    verify_export: bool = True

    @field_validator("default_folder")
    @classmethod
    def validate_default_folder(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Default export folder cannot be empty.")
        return value.strip()


class BrowserSettings(ContextVaultModel):
    """Google Chrome and persistent profile configuration."""

    browser: str = SUPPORTED_BROWSER
    user_data_dir: str = ""
    profile_directory: str = "Default"
    cdp_endpoint: str = DEFAULT_CDP_ENDPOINT
    start_url: str = "https://chatgpt.com/"

    @field_validator("browser")
    @classmethod
    def validate_browser(cls, value: str) -> str:
        if value != SUPPORTED_BROWSER:
            raise ValueError("ContextVault supports Google Chrome only.")
        return value

    @field_validator("profile_directory")
    @classmethod
    def validate_profile_directory(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Chrome profile directory cannot be empty.")
        if (
            Path(clean).is_absolute()
            or clean in {".", ".."}
            or "/" in clean
            or "\\" in clean
            or "\x00" in clean
        ):
            raise ValueError("Profile directory must be a Chrome profile name, not a path.")
        return clean


class PerformanceSettings(ContextVaultModel):
    """Worker and extraction performance controls."""

    worker_threads: int = Field(default=4, ge=1, le=8)
    message_retry_count: int = Field(default=5, ge=1, le=20)
    delay_mode: str = "Normal"
    memory_mode: str = "Balanced"

    @field_validator("worker_threads")
    @classmethod
    def validate_worker_threads(cls, value: int) -> int:
        if value not in {1, 2, 4, 8}:
            raise ValueError("Worker threads must be one of 1, 2, 4, or 8.")
        return value

    @field_validator("delay_mode")
    @classmethod
    def validate_delay_mode(cls, value: str) -> str:
        if value not in {"Auto", "Fast", "Normal", "Safe"}:
            raise ValueError("Unsupported delay mode.")
        return value

    @field_validator("memory_mode")
    @classmethod
    def validate_memory_mode(cls, value: str) -> str:
        if value not in {"Low", "Balanced", "High"}:
            raise ValueError("Unsupported memory mode.")
        return value


class ApplicationSettings(ContextVaultModel):
    """Complete user-editable configuration."""

    schema_version: str = "1.0"
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    export: ExportSettings = Field(default_factory=ExportSettings)
    assets: AssetSettings = Field(default_factory=AssetSettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
