"""Shared Pydantic model configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    """Convert snake_case names to camelCase JSON keys."""
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ContextVaultModel(BaseModel):
    """Base model with deterministic camelCase serialization."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
        validate_assignment=True,
        str_strip_whitespace=False,
    )
