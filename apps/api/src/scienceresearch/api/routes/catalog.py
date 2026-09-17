"""Target v1 catalog and research workflow map routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ...application.catalog import CatalogUseCase
from ..dto.catalog import CatalogDTO, ResearchWorkflowMapDTO

router = APIRouter(prefix="/api/v1", tags=["catalog"])


def catalog_use_case(request: Request) -> CatalogUseCase:
    use_case: CatalogUseCase = request.app.state.catalog_use_case
    return use_case


CatalogDependency = Annotated[CatalogUseCase, Depends(catalog_use_case)]


@router.get("/catalog", response_model=CatalogDTO)
def catalog(use_case: CatalogDependency) -> CatalogDTO:
    snapshot = use_case.catalog()
    return CatalogDTO.model_validate(snapshot, from_attributes=True)


@router.get(
    "/research-workflow-map",
    response_model=ResearchWorkflowMapDTO,
    responses={503: {"description": "Workflow map configuration is unavailable or invalid"}},
)
def research_workflow_map(use_case: CatalogDependency) -> ResearchWorkflowMapDTO:
    snapshot = use_case.research_workflow_map()
    return ResearchWorkflowMapDTO.model_validate(
        {
            "version": snapshot.version,
            "workflows": [
                {
                    "id": workflow.id,
                    "stage": workflow.stage,
                    "stage_name": workflow.stage_name,
                    "name": workflow.name,
                    "owner_role": workflow.owner_role,
                    "description": workflow.description,
                    "outputs": list(workflow.outputs),
                    "work_package_ids": list(workflow.work_package_ids),
                }
                for workflow in snapshot.workflows
            ],
        }
    )
