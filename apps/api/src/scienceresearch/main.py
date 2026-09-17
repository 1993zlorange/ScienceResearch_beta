"""FastAPI composition root for the incremental ScienceResearch migration."""

from __future__ import annotations

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

from .adapters.catalog.research_workflow_map import FileResearchWorkflowMapAdapter
from .adapters.legacy.catalog import LegacyCatalogAdapter
from .adapters.persistence.context_repository import PostgresContextRepository
from .adapters.persistence.session import create_postgres_engine, create_unit_of_work
from .api.errors import install_error_handlers
from .api.routes import catalog_router, contexts_router, health_router
from .application.catalog import CatalogUseCase
from .application.context import ContextUseCase
from .application.readiness import ReadinessUseCase
from .flask_app import create_app as create_flask_app
from .settings import Environment, Settings


class PathPreservingWSGIMiddleware(WSGIMiddleware):
    """Keep the original request path when composing the transitional Flask app."""

    async def __call__(self, scope: MutableMapping[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            scope = {**scope, "root_path": ""}
        await super().__call__(scope, receive, send)


def create_app(
    *,
    settings: Settings | None = None,
    legacy_data_dir: Path | None = None,
    frontend_dist: Path | None = None,
    readiness_engine: Any | None = None,
    context_use_case: ContextUseCase | None = None,
    include_legacy: bool = True,
) -> FastAPI:
    """Compose target API boundaries and the frozen same-origin legacy bridge."""
    resolved_settings = settings or Settings()
    app = FastAPI(
        title="ScienceResearch API",
        version="0.2.0",
        openapi_url="/api/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],  # Same-origin deployment; no wildcard proxy exposure.
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(catalog_router)
    app.include_router(contexts_router)
    app.state.settings = resolved_settings
    app.state.readiness_probe = ReadinessUseCase()

    if readiness_engine is None and resolved_settings.environment is not Environment.LOCAL:
        readiness_engine = create_postgres_engine(resolved_settings.sqlalchemy_database_url)
    app.state.readiness_engine = readiness_engine
    app.state.context_use_case = context_use_case
    app.state.context_engine = None

    if include_legacy:
        flask_app = create_flask_app(data_dir=legacy_data_dir, frontend_dist=frontend_dist)
        app.state.legacy_app = flask_app
        workbench = flask_app.extensions["scienceresearch_workbench"]
        workflow_map_source = (
            Path(__file__).resolve().parents[4] / "database" / "seeds" / "catalog" / "research-workflow-map-v1.json"
        )
        catalog_use_case = CatalogUseCase(
            LegacyCatalogAdapter(workbench),
            FileResearchWorkflowMapAdapter(workflow_map_source),
        )
        app.state.catalog_use_case = catalog_use_case
        if context_use_case is None:
            context_engine = create_postgres_engine(resolved_settings.sqlalchemy_database_url)
            app.state.context_engine = context_engine
            app.state.context_use_case = ContextUseCase(
                PostgresContextRepository(
                    create_unit_of_work(context_engine),
                    resolved_settings.artifact_root,
                ),
                catalog_use_case.catalog(),
            )
        # Target routes are matched first; unmatched same-origin DOM compatibility
        # paths remain served by the Flask adapter, not an iframe.
        app.mount("/", PathPreservingWSGIMiddleware(flask_app), name="legacy")
    else:
        app.state.legacy_app = None
        app.state.catalog_use_case = None

    return app
