"""Argon2 password hashing implementation."""

from pwdlib import PasswordHash

from application.ports.password_hasher import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    """Hash and verify passwords using Argon2."""

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def hash(self, password: str) -> str:
        """Return an Argon2 hash for a plaintext password."""

        if not password:
            raise ValueError("password cannot be empty.")

        return self._password_hash.hash(password)

    def verify(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        """Verify a plaintext password against an Argon2 hash."""

        if not password or not password_hash:
            return False

        try:
            return self._password_hash.verify(
                password,
                password_hash,
            )
        except Exception:
            return False