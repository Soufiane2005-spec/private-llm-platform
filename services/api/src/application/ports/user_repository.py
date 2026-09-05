"""Repository port for platform users."""

from typing import Protocol

from domain.auth.user import PlatformUser


class UserRepository(Protocol):
    """Persist and retrieve platform users."""

    def save(self, user: PlatformUser) -> None:
        """Create or replace a user."""

    def get(self, username: str) -> PlatformUser | None:
        """Return a user by username."""

    def list(self) -> tuple[PlatformUser, ...]:
        """Return all users."""

    def delete(self, username: str) -> None:
        """Delete a user if it exists."""
