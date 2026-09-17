"""Compatibility adapter for the pre-boundary implementation.

This module is the only new-boundary adapter that knows about the legacy core.
It can be replaced module by module without changing application callers.
"""

from __future__ import annotations

from ..core import ResearchWorkbench
from ..domain.errors import AppError

__all__ = ["AppError", "ResearchWorkbench"]
