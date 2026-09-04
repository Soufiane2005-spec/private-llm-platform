"""Typed application configuration loaded from environment variables."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from domain.auth.user import UserRole

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


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

    auth_secret_key: str = (
        "development-only-secret-change-before-production"
    )
    auth_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = 30

    auth_admin_username: str = "admin"
    auth_admin_role: UserRole = UserRole.ADMIN

    auth_admin_password_hash: str = (
        "$argon2id$v=19$m=65536,t=3,p=4$"
        "OC8zX5IzQU7QwTpcN31dPQ$"
        "TlHBjjWGUeKzB6Sla1jU8HmJTUYbQ82gRjdB0iBkRwM"
    )

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_timeout_seconds: float = 120.0

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()
