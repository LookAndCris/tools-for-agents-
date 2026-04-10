"""Application settings loaded from environment variables via pydantic-settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Top-level configuration for the application.

    Values are read from environment variables or from a ``.env`` file
    located in the project root.  All fields have sensible defaults for
    local development; override them in staging/production environments.
    """

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tools_for_agents"
    app_env: str = "development"

    # API server settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    allowed_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Singleton for application-wide use.
settings = Settings()
