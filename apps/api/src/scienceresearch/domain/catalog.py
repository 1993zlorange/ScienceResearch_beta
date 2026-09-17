"""Pure catalog snapshot types used by application and adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .json_values import JsonValue


@dataclass(frozen=True, slots=True)
class WorkPackageSnapshot:
    """A stable catalog work package value."""

    id: str
    name: str
    action: str
    deliverable: str
    template: Mapping[str, JsonValue]
    skill: Mapping[str, JsonValue]
    category: str
    stage: str
    next_step_definition: Mapping[str, JsonValue]


@dataclass(frozen=True, slots=True)
class CatalogAreaSnapshot:
    """A stable catalog area value."""

    id: str
    name: str
    work_packages: tuple[WorkPackageSnapshot, ...]


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    """Validated catalog data independent of HTTP and persistence."""

    version: str
    areas: tuple[CatalogAreaSnapshot, ...]

    @property
    def work_package_count(self) -> int:
        return sum(len(area.work_packages) for area in self.areas)


@dataclass(frozen=True, slots=True)
class ResearchWorkflowSnapshot:
    """A stable AI4SCIENCE workflow boundary mapped to catalog packages."""

    id: str
    stage: str
    stage_name: str
    name: str
    owner_role: str
    description: str
    outputs: tuple[str, ...]
    work_package_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResearchWorkflowMapSnapshot:
    """Validated read-only workflow map; it is not per-context execution state."""

    version: str
    workflows: tuple[ResearchWorkflowSnapshot, ...]
