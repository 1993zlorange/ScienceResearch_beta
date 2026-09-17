"""Stable API error mapping for target FastAPI routes."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..domain.errors import AppError
from .dto.errors import APIErrorDTO


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) and request_id else uuid4().hex


def install_error_handlers(app: FastAPI) -> None:
    """Assign opaque request IDs and map errors without leaking stack traces."""

    original_openapi = app.openapi

    def openapi_with_error_contract() -> dict[str, Any]:
        schema = original_openapi()
        components = schema.setdefault("components", {})
        schemas = components.setdefault("schemas", {})
        schemas.setdefault(
            "APIErrorDTO",
            APIErrorDTO.model_json_schema(ref_template="#/components/schemas/{model}"),
        )
        app.openapi_schema = schema
        return schema

    app.openapi = openapi_with_error_contract  # type: ignore[method-assign]

    @app.middleware("http")
    async def assign_request_id(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request.state.request_id = uuid4().hex
        return await call_next(request)

    @app.exception_handler(AppError)
    async def application_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=APIErrorDTO(
                code=exc.code,
                detail=exc.message,
                requestId=_request_id(request),
            ).model_dump(mode="json"),
            media_type="application/problem+json",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        del exc
        return JSONResponse(
            status_code=422,
            content=APIErrorDTO(
                code="INVALID_INPUT",
                detail="请求参数无效",
                requestId=_request_id(request),
            ).model_dump(mode="json"),
            media_type="application/problem+json",
        )
