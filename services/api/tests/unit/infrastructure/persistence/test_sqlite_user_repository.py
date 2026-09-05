"""Tests for SQLite user persistence."""

from domain.auth.user import PlatformUser, UserRole
from infrastructure.persistence.sqlite_user_repository import SQLiteUserRepository


def test_sqlite_user_repository_persists_users(tmp_path) -> None:
    """Users survive repository re-creation."""

    database_path = tmp_path / "platform.db"
    repository = SQLiteUserRepository(database_path)
    repository.save(
        PlatformUser(
            username="engineer",
            password_hash="hash",
            role=UserRole.ENGINEER,
        )
    )

    reloaded = SQLiteUserRepository(database_path)

    assert reloaded.get("engineer") == PlatformUser(
        username="engineer",
        password_hash="hash",
        role=UserRole.ENGINEER,
    )


def test_sqlite_user_repository_updates_and_deletes_user(tmp_path) -> None:
    """Users can be updated and deleted."""

    repository = SQLiteUserRepository(tmp_path / "platform.db")
    repository.save(
        PlatformUser(
            username="viewer",
            password_hash="old-hash",
            role=UserRole.VIEWER,
        )
    )
    repository.save(
        PlatformUser(
            username="viewer",
            password_hash="new-hash",
            role=UserRole.ENGINEER,
            is_active=False,
        )
    )

    assert repository.list() == (
        PlatformUser(
            username="viewer",
            password_hash="new-hash",
            role=UserRole.ENGINEER,
            is_active=False,
        ),
    )

    repository.delete("viewer")

    assert repository.get("viewer") is None
