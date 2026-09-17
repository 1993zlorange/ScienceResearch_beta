"""Stable application boundary retained during incremental migration."""

from __future__ import annotations

from typing import Protocol


class WorkbenchPort(Protocol):
    """Application-facing service contract; implementation is composed externally."""

    def catalog(self) -> dict[str, object]: ...


__all__ = ["WorkbenchPort"]
