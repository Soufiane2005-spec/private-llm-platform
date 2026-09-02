"""Authentication token application port."""

from typing import Protocol

from domain.auth.user import UserRole


class TokenService(Protocol):
    """Access token creation and validation contract."""

    def create_access_token(
        self,
        subject: str,
        role: UserRole,
    ) -> str:
        """Create an access token for a subject and role."""
        ...

    def get_identity(
        self,
        token: str,
    ) -> tuple[str, UserRole]:
        """Extract and validate token identity."""
        ...