"""Pydantic DTOs for the target v1 catalog API."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]+$")]


class WorkPackageDTO(BaseModel):
    """Public work package contract; nested catalog assets remain JSON-typed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Identifier
    name: str = Field(min_length=1)
    action: str = Field(min_length=1)
    deliverable: str = Field(min_length=1)
    template: dict[str, JsonValue]
    skill: dict[str, JsonValue]
    category: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    next_step_definition: dict[str, JsonValue]


class CatalogAreaDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Identifier
    name: str = Field(min_length=1)
    work_packages: list[WorkPackageDTO] = Field(min_length=1)


class CatalogDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(min_length=1)
    areas: list[CatalogAreaDTO] = Field(min_length=1)


class ReadinessDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    database: str


class ResearchWorkflowDTO(BaseModel):
    """Public AI4SCIENCE workflow boundary; it is not a context workflow row."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Identifier
    stage: str = Field(pattern=r"^(Explore|Execute|Express)$")
    stage_name: str = Field(min_length=1)
    name: str = Field(min_length=1)
    owner_role: str = Field(min_length=1)
    description: str = Field(min_length=1)
    outputs: list[str] = Field(min_length=1)
    work_package_ids: list[Identifier] = Field(min_length=1)


class ResearchWorkflowMapDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(min_length=1)
    workflows: list[ResearchWorkflowDTO] = Field(min_length=1)
