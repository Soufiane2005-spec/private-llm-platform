"""Authentication and authorization user domain models."""

from dataclasses import dataclass
from enum import StrEnum


class UserRole(StrEnum):
    """Supported platform authorization roles."""

    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"


@dataclass(frozen=True, slots=True)
class AuthUser:
    """Authenticated platform user."""

    username: str
    role: UserRole

    def __post_init__(self) -> None:
        """Validate authenticated user invariants."""

        if not self.username.strip():
            raise ValueError("username cannot be empty.")