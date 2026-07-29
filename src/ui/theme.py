"""Frozen ContextVault CustomTkinter theme tokens."""

from __future__ import annotations

import customtkinter as ctk

from src.config.constants import THEME_COLORS

BACKGROUND = THEME_COLORS["background"]
CARD = THEME_COLORS["card"]
BORDER = THEME_COLORS["border"]
PRIMARY = THEME_COLORS["primary"]
SUCCESS = THEME_COLORS["success"]
WARNING = THEME_COLORS["warning"]
DANGER = THEME_COLORS["danger"]
TEXT = THEME_COLORS["text"]
MUTED = THEME_COLORS["muted"]


def configure_theme() -> None:
    """Apply the frozen dark-only v1 appearance."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
