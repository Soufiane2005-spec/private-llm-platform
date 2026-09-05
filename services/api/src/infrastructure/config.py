"""Typed application configuration loaded from environment variables."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from domain.auth.user import UserRole

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
DEFAULT_CORS_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
)


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
    cors_allowed_origins: str = ",".join(DEFAULT_CORS_ALLOWED_ORIGINS)
    database_url: str = "sqlite:///./data/platform.db"
    prometheus_base_url: str | None = None
    model_deployment_backend: str = "local"
    kubernetes_namespace: str = "llm-platform"

    @property
    def allowed_cors_origins(self) -> tuple[str, ...]:
        """Return configured browser origins allowed to call the API."""

        return tuple(
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        )

    @property
    def sqlite_database_path(self) -> Path:
        """Return the SQLite path configured for local persistence."""

        prefix = "sqlite:///"

        if not self.database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// DATABASE_URL values are supported.")

        configured_path = Path(self.database_url.removeprefix(prefix))

        if configured_path.is_absolute():
            return configured_path

        return ENV_FILE.parent / configured_path

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
