"""Target health and readiness routes."""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from ...application.readiness import ReadinessEngine, ReadinessUseCase
from ..dto.catalog import ReadinessDTO

router = APIRouter(tags=["health"])


@router.get("/healthz")
def health() -> dict[str, str]:
    """Return liveness without opening a database connection."""
    return {"service": "scienceresearch", "status": "ok"}


@router.get(
    "/readyz",
    response_model=ReadinessDTO,
    status_code=status.HTTP_200_OK,
    responses={503: {"description": "PostgreSQL or schema is not ready"}},
)
def readiness(request: Request) -> ReadinessDTO | JSONResponse:
    probe: ReadinessUseCase | None = request.app.state.readiness_probe
    engine: ReadinessEngine | None = request.app.state.readiness_engine
    if probe is None or engine is None:
        return JSONResponse(
            status_code=503,
            content=ReadinessDTO(status="unavailable", database="not_configured").model_dump(),
            media_type="application/problem+json",
        )
    if not probe.is_ready(engine):
        return JSONResponse(
            status_code=503,
            content=ReadinessDTO(status="unavailable", database="error").model_dump(),
            media_type="application/problem+json",
        )
    return ReadinessDTO(status="ready", database="ready")
