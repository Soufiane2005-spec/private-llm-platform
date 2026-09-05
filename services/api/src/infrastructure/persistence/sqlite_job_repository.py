"""SQLite-backed asynchronous job repository."""

import sqlite3
from contextlib import closing
from pathlib import Path

from domain.jobs.job import Job, JobStatus


class SQLiteJobRepository:
    """Persist jobs in SQLite."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save(self, job: Job) -> None:
        """Store or replace a job."""

        with closing(self._connect()) as connection:
            connection.execute(
                """
                insert into jobs (
                    job_id, job_type, status, error, attempts, max_attempts
                )
                values (?, ?, ?, ?, ?, ?)
                on conflict(job_id) do update set
                    job_type = excluded.job_type,
                    status = excluded.status,
                    error = excluded.error,
                    attempts = excluded.attempts,
                    max_attempts = excluded.max_attempts
                """,
                (
                    job.job_id,
                    job.job_type,
                    job.status.value,
                    job.error,
                    job.attempts,
                    job.max_attempts,
                ),
            )
            connection.commit()

    def get(self, job_id: str) -> Job | None:
        """Return a job by identifier."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                select job_id, job_type, status, error, attempts, max_attempts
                from jobs
                where job_id = ?
                """,
                (job_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_job(row)

    def list(self) -> tuple[Job, ...]:
        """Return all jobs ordered by identifier."""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                select job_id, job_type, status, error, attempts, max_attempts
                from jobs
                order by job_id
                """
            ).fetchall()

        return tuple(self._row_to_job(row) for row in rows)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                create table if not exists jobs (
                    job_id text primary key,
                    job_type text not null,
                    status text not null,
                    error text,
                    attempts integer not null,
                    max_attempts integer not null
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            job_id=row["job_id"],
            job_type=row["job_type"],
            status=JobStatus(row["status"]),
            error=row["error"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
        )
