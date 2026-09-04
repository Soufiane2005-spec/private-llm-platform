"""SQLite-backed platform user repository."""

import sqlite3
from contextlib import closing
from pathlib import Path

from domain.auth.user import PlatformUser, UserRole


class SQLiteUserRepository:
    """Persist platform users in SQLite."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save(self, user: PlatformUser) -> None:
        """Create or replace a user."""

        with closing(self._connect()) as connection:
            connection.execute(
                """
                insert into users (username, password_hash, role, is_active)
                values (?, ?, ?, ?)
                on conflict(username) do update set
                    password_hash = excluded.password_hash,
                    role = excluded.role,
                    is_active = excluded.is_active
                """,
                (
                    user.username,
                    user.password_hash,
                    user.role.value,
                    int(user.is_active),
                ),
            )
            connection.commit()

    def get(self, username: str) -> PlatformUser | None:
        """Return a user by username."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                select username, password_hash, role, is_active
                from users
                where username = ?
                """,
                (username,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_user(row)

    def list(self) -> tuple[PlatformUser, ...]:
        """Return all users ordered by username."""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                select username, password_hash, role, is_active
                from users
                order by username
                """
            ).fetchall()

        return tuple(self._row_to_user(row) for row in rows)

    def delete(self, username: str) -> None:
        """Delete a user if it exists."""

        with closing(self._connect()) as connection:
            connection.execute(
                "delete from users where username = ?",
                (username,),
            )
            connection.commit()

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                create table if not exists users (
                    username text primary key,
                    password_hash text not null,
                    role text not null,
                    is_active integer not null
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> PlatformUser:
        return PlatformUser(
            username=row["username"],
            password_hash=row["password_hash"],
            role=UserRole(row["role"]),
            is_active=bool(row["is_active"]),
        )
