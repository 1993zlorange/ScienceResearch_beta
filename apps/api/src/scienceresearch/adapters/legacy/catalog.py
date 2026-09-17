"""Transitional catalog adapter backed by the frozen legacy workbench."""

from __future__ import annotations

from typing import Any

from ...domain.catalog import CatalogAreaSnapshot, CatalogSnapshot, WorkPackageSnapshot
from ...domain.json_values import JsonValue


def _json_value(value: Any) -> JsonValue:
    """Validate recursive JSON-compatible values without silently coercing them."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("catalog JSON object keys must be strings")
        return {key: _json_value(item) for key, item in value.items()}
    raise ValueError(f"unsupported catalog value: {type(value).__name__}")


def _mapping(value: Any, field: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError(f"catalog {field} must be an object")
    result: dict[str, JsonValue] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"catalog {field} keys must be strings")
        result[key] = _json_value(item)
    return result


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"catalog {field} must be a non-empty string")
    return value


class LegacyCatalogAdapter:
    """Read the frozen legacy catalog; no new business logic is permitted here."""

    def __init__(self, workbench: Any) -> None:
        self._workbench = workbench

    def catalog(self, *, read_only: bool = True) -> CatalogSnapshot:
        raw = self._workbench.catalog(read_only=read_only)
        if not isinstance(raw, dict):
            raise ValueError("legacy catalog response must be an object")
        raw_areas = raw.get("areas")
        if not isinstance(raw_areas, list):
            raise ValueError("legacy catalog areas must be an array")
        areas = tuple(self._area(item) for item in raw_areas)
        return CatalogSnapshot(version=_text(raw.get("version"), "version"), areas=areas)

    def _area(self, value: Any) -> CatalogAreaSnapshot:
        if not isinstance(value, dict):
            raise ValueError("catalog area must be an object")
        raw_packages = value.get("work_packages")
        if not isinstance(raw_packages, list):
            raise ValueError("catalog work_packages must be an array")
        return CatalogAreaSnapshot(
            id=_text(value.get("id"), "area.id"),
            name=_text(value.get("name"), "area.name"),
            work_packages=tuple(self._work_package(item) for item in raw_packages),
        )

    def _work_package(self, value: Any) -> WorkPackageSnapshot:
        if not isinstance(value, dict):
            raise ValueError("catalog work package must be an object")
        return WorkPackageSnapshot(
            id=_text(value.get("id"), "work_package.id"),
            name=_text(value.get("name"), "work_package.name"),
            action=_text(value.get("action"), "work_package.action"),
            deliverable=_text(value.get("deliverable"), "work_package.deliverable"),
            template=_mapping(value.get("template"), "work_package.template"),
            skill=_mapping(value.get("skill"), "work_package.skill"),
            category=_text(value.get("category"), "work_package.category"),
            stage=_text(value.get("stage"), "work_package.stage"),
            next_step_definition=_mapping(value.get("next_step_definition"), "work_package.next_step_definition"),
        )
