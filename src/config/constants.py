"""Application-wide immutable constants."""

from __future__ import annotations

from pathlib import Path

APPLICATION_NAME = "ContextVault"
APPLICATION_VERSION = "0.2.1"
ARCHIVE_FORMAT = "contextvault"
ARCHIVE_SCHEMA_VERSION = "1.0"
DEFAULT_WINDOW_SIZE = "1180x760"
MINIMUM_WINDOW_SIZE = (1000, 680)
DEFAULT_EXPORT_DIRECTORY_NAME = "exports"
DEFAULT_LOG_DIRECTORY_NAME = "logs"
DEFAULT_DATA_DIRECTORY_NAME = "data"
DEFAULT_CONFIG_FILENAME = "settings.json"
EXPORT_HISTORY_FILENAME = "export_history.json"
DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:9222"
DEFAULT_CHAT_URL = "https://chatgpt.com/"
SUPPORTED_BROWSER = "Chrome"
SUPPORTED_ASSET_EXTENSIONS = {
    ".7z",
    ".bmp",
    ".pdf",
    ".zip",
    ".csv",
    ".doc",
    ".txt",
    ".docx",
    ".gif",
    ".html",
    ".jpeg",
    ".jpg",
    ".json",
    ".md",
    ".ods",
    ".odt",
    ".png",
    ".ppt",
    ".pptx",
    ".py",
    ".rar",
    ".rtf",
    ".tar",
    ".tsv",
    ".webp",
    ".xls",
    ".xlsx",
    ".xml",
    ".yaml",
    ".yml",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
REQUIRED_ARCHIVE_FILES = (
    "manifest.json",
    "metadata.json",
    "conversation.json",
    "conversation.md",
    "summary.json",
    "search-index.json",
    "statistics.json",
    "rag/chunks.json",
    "rag/documents.json",
    "rag/keywords.json",
    "rag/chunk-map.json",
    "logs/export.log",
    "logs/validation.log",
)
REQUIRED_ARCHIVE_DIRECTORIES = (
    "assets/code",
    "assets/images",
    "assets/attachments",
    "assets/tables",
    "assets/citations",
    "rag",
    "logs",
)
CODE_EXTENSION_BY_LANGUAGE = {
    "python": ".py",
    "py": ".py",
    "javascript": ".js",
    "js": ".js",
    "typescript": ".ts",
    "ts": ".ts",
    "html": ".html",
    "css": ".css",
    "json": ".json",
    "yaml": ".yaml",
    "yml": ".yml",
    "xml": ".xml",
    "bash": ".sh",
    "shell": ".sh",
    "powershell": ".ps1",
    "sql": ".sql",
    "markdown": ".md",
    "text": ".txt",
}
THEME_COLORS = {
    "background": "#0F1117",
    "card": "#161B22",
    "border": "#242938",
    "primary": "#3B82F6",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
}

PROJECT_ROOT_MARKERS = ("pyproject.toml", "vibproject.ygit")


def archive_required_paths(root: Path) -> tuple[Path, ...]:
    """Return all required archive paths relative to *root*."""
    return tuple(root / item for item in (*REQUIRED_ARCHIVE_FILES, *REQUIRED_ARCHIVE_DIRECTORIES))
