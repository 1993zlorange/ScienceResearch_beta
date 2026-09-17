"""SQLAlchemy persistence boundary shared by PostgreSQL adapters."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Self

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ...domain.errors import AppError


class Base(DeclarativeBase):
    """Base for target ORM mappings; legacy tables are not mapped here."""


class PostgresUnitOfWork:
    """Owns one transaction per use case; routes never hold sessions."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def session(self) -> Iterator[Session]:
        try:
            with self._session_factory() as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
        except SQLAlchemyError as exc:
            raise AppError("DATABASE_UNAVAILABLE", "database is unavailable", 503) from exc


def create_postgres_engine(database_url: str) -> Engine:
    """Create a PostgreSQL engine with bounded connection setup time."""
    if not database_url.startswith("postgresql+psycopg://"):
        raise ValueError("target engine requires PostgreSQL with psycopg")
    return create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


def create_unit_of_work(engine: Engine) -> PostgresUnitOfWork:
    return PostgresUnitOfWork(sessionmaker(bind=engine, expire_on_commit=False))


class EngineFactory:
    """Explicit factory so application code can depend on a narrow protocol."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def __enter__(self) -> Self:
        self.engine = create_postgres_engine(self._database_url)
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.engine.dispose()
