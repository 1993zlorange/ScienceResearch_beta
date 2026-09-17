"""File adapter for the approved read-only AI4SCIENCE workflow mapping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...domain.catalog import ResearchWorkflowMapSnapshot, ResearchWorkflowSnapshot
from ...domain.errors import AppError

_ALLOWED_STAGES = {"Explore", "Execute", "Express"}


class FileResearchWorkflowMapAdapter:
    """Load and shape a versioned JSON seed without touching transport state."""

    def __init__(self, source: Path) -> None:
        self._source = source

    def research_workflow_map(self) -> ResearchWorkflowMapSnapshot:
        try:
            raw = json.loads(self._source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AppError("WORKFLOW_MAP_INVALID", "research workflow map source is unreadable", 503) from error
        if not isinstance(raw, dict):
            raise AppError("WORKFLOW_MAP_INVALID", "research workflow map must be an object", 503)
        version = _text(raw.get("version"), "version")
        raw_workflows = raw.get("workflows")
        if not isinstance(raw_workflows, list) or not raw_workflows:
            raise AppError("WORKFLOW_MAP_INVALID", "research workflow map workflows must be a non-empty array", 503)
        workflows = tuple(self._workflow(item) for item in raw_workflows)
        return ResearchWorkflowMapSnapshot(version=version, workflows=workflows)

    def _workflow(self, value: Any) -> ResearchWorkflowSnapshot:
        if not isinstance(value, dict):
            raise AppError("WORKFLOW_MAP_INVALID", "research workflow must be an object", 503)
        stage = _text(value.get("stage"), "workflow.stage")
        if stage not in _ALLOWED_STAGES:
            raise AppError("WORKFLOW_MAP_INVALID", "research workflow stage is invalid", 503)
        outputs = _strings(value.get("outputs"), "workflow.outputs")
        package_ids = _strings(value.get("work_package_ids"), "workflow.work_package_ids")
        return ResearchWorkflowSnapshot(
            id=_text(value.get("id"), "workflow.id"),
            stage=stage,
            stage_name=_text(value.get("stage_name"), "workflow.stage_name"),
            name=_text(value.get("name"), "workflow.name"),
            owner_role=_text(value.get("owner_role"), "workflow.owner_role"),
            description=_text(value.get("description"), "workflow.description"),
            outputs=outputs,
            work_package_ids=package_ids,
        )


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AppError("WORKFLOW_MAP_INVALID", f"research workflow map {field} must be a non-empty string", 503)
    return value


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise AppError("WORKFLOW_MAP_INVALID", f"research workflow map {field} must be a non-empty array", 503)
    return tuple(_text(item, field) for item in value)
