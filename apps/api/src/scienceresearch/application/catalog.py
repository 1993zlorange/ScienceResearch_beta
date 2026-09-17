"""Application use cases for reading the approved research catalog and workflow map."""

from __future__ import annotations

from typing import Protocol

from ..domain.catalog import CatalogSnapshot, ResearchWorkflowMapSnapshot
from ..domain.errors import AppError

_ALLOWED_WORKFLOW_IDS = frozenset(
    {
        "PI-E01",
        "MB-E01",
        "CR-E01",
        "EX-E01",
        "PI-X01",
        "MB-X01",
        "EX-X01",
        "CR-X01",
        "EX-P01",
        "MB-P01",
        "PI-P01",
        "CR-P01",
    }
)


class CatalogPort(Protocol):
    """Read-only boundary for a catalog source during migration."""

    def catalog(self, *, read_only: bool = True) -> CatalogSnapshot: ...


class ResearchWorkflowMapPort(Protocol):
    """Read-only boundary for the approved AI4SCIENCE workflow mapping."""

    def research_workflow_map(self) -> ResearchWorkflowMapSnapshot: ...


class CatalogUseCase:
    """Return validated catalog reference data without exposing transport details."""

    def __init__(
        self,
        port: CatalogPort,
        workflow_map_port: ResearchWorkflowMapPort | None = None,
    ) -> None:
        self._port = port
        self._workflow_map_port = workflow_map_port

    def catalog(self) -> CatalogSnapshot:
        snapshot = self._port.catalog(read_only=True)
        if len(snapshot.areas) != 8 or snapshot.work_package_count != 68:
            raise ValueError("catalog must contain exactly 8 areas and 68 work packages")
        return snapshot

    def research_workflow_map(self) -> ResearchWorkflowMapSnapshot:
        if self._workflow_map_port is None:
            raise AppError("WORKFLOW_MAP_UNAVAILABLE", "research workflow map is not configured", 503)
        catalog = self.catalog()
        snapshot = self._workflow_map_port.research_workflow_map()
        workflow_ids = [workflow.id for workflow in snapshot.workflows]
        mapped_ids = [package_id for workflow in snapshot.workflows for package_id in workflow.work_package_ids]
        catalog_ids = [package.id for area in catalog.areas for package in area.work_packages]
        if len(snapshot.workflows) != 12 or len(set(workflow_ids)) != 12 or set(workflow_ids) != _ALLOWED_WORKFLOW_IDS:
            raise AppError("WORKFLOW_MAP_INVALID", "research workflow map workflow IDs are invalid", 503)
        if len(mapped_ids) != 68 or len(set(mapped_ids)) != 68 or set(mapped_ids) != set(catalog_ids):
            raise AppError(
                "WORKFLOW_MAP_INVALID",
                "research workflow map must cover all 68 catalog work packages exactly once",
                503,
            )
        return snapshot
