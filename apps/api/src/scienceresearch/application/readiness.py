"""Application readiness boundary independent of a concrete database driver."""

from __future__ import annotations

from typing import Protocol


class _Result(Protocol):
    def scalar_one_or_none(self) -> object | None: ...


class _Connection(Protocol):
    def exec_driver_sql(self, statement: str) -> _Result: ...
    def __enter__(self) -> _Connection: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None: ...


class ReadinessEngine(Protocol):
    def connect(self) -> _Connection: ...


class ReadinessUseCase:
    """Check database reachability and the installed Alembic version."""

    def is_ready(self, engine: ReadinessEngine) -> bool:
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
                version = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one_or_none()
                return version is not None
        except Exception:
            return False
