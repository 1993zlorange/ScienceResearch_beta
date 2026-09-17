"""FastAPI route boundary; DTOs are defined in api.dto."""

from .errors import install_error_handlers

__all__ = ["install_error_handlers"]
