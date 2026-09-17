"""Shared error response contracts for target API routes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class APIErrorDTO(BaseModel):
    """Stable problem payload used by every target API error response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, examples=["INVALID_INPUT"])
    detail: str = Field(min_length=1, examples=["请求参数无效"])
    requestId: str = Field(
        min_length=1,
        pattern="^[0-9a-f]{32}$",
        examples=["5f0d5b3a6cbf4f21916d1bd5f47b28c1"],
    )


__all__ = ["APIErrorDTO"]
