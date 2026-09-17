"""Pydantic-based runtime settings with secrets excluded from representations."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Validated process settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="SCIENCERESEARCH_", extra="ignore", frozen=True)

    environment: Environment = Environment.LOCAL
    database_url: str = Field(
        default="postgresql+psycopg://scienceresearch:scienceresearch@localhost:5432/scienceresearch"
    )
    artifact_root: Path = Path("storage/artifacts")
    model_api_key: SecretStr | None = None
    model_timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR)$")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        allowed = ("postgresql://", "postgresql+psycopg://")
        if not value.startswith(allowed):
            raise ValueError("database_url must use PostgreSQL with psycopg")
        if "*" in value or "\n" in value or "\r" in value:
            raise ValueError("database_url contains invalid characters")
        return value

    @property
    def sqlalchemy_database_url(self) -> str:
        return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
