"""Authentication user domain model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthUser:
    """Authenticated platform user."""

    username: str

    def __post_init__(self) -> None:
        """Validate authenticated user invariants."""

        if not self.username.strip():
            raise ValueError("username cannot be empty.")