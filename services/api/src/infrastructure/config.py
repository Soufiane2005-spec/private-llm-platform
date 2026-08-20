"""Typed application configuration loaded from environment variables."""

from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    """Supported application environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Runtime configuration for the backend API."""

    app_name: str = "private-llm-platform"
    app_version: str = "0.1.0"
    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()