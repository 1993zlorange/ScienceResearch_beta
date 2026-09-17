"""Target API route package."""

from .catalog import router as catalog_router
from .contexts import router as contexts_router
from .health import router as health_router

__all__ = ["catalog_router", "contexts_router", "health_router"]
