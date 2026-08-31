"""Password hashing application port."""

from typing import Protocol


class PasswordHasher(Protocol):
    """Password hashing and verification contract."""

    def hash(self, password: str) -> str:
        """Hash a plaintext password."""
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        """Verify a plaintext password against a stored hash."""
        ...