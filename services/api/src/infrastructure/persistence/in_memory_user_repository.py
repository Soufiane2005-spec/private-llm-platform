"""In-memory platform user repository."""

from domain.auth.user import PlatformUser


class InMemoryUserRepository:
    """Store platform users in memory by username."""

    def __init__(self, users: tuple[PlatformUser, ...] = ()) -> None:
        self._users = {user.username: user for user in users}

    def save(self, user: PlatformUser) -> None:
        """Create or replace a user."""

        self._users[user.username] = user

    def get(self, username: str) -> PlatformUser | None:
        """Return a user by username."""

        return self._users.get(username)

    def list(self) -> tuple[PlatformUser, ...]:
        """Return users in deterministic order."""

        return tuple(self._users[username] for username in sorted(self._users))

    def delete(self, username: str) -> None:
        """Delete a user if it exists."""

        self._users.pop(username, None)
