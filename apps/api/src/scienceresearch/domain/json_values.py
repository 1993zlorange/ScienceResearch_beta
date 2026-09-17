"""Typed JSON-compatible values shared by domain catalog objects."""

from __future__ import annotations

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
