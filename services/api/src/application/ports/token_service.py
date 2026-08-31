"""Authentication token application port."""

from typing import Protocol


class TokenService(Protocol):
    """Access token creation and validation contract."""

    def create_access_token(self, subject: str) -> str:
        """Create an access token for a subject."""
        ...

    def get_subject(self, token: str) -> str:
        """Extract and validate the token subject."""
        ...