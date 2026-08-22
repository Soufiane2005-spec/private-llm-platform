"""Application port for job persistence."""

from typing import Protocol

from domain.jobs.job import Job


class JobRepository(Protocol):
    """Persistence contract for asynchronous jobs."""

    def save(self, job: Job) -> None:
        """Store or replace a job."""
        ...

    def get(self, job_id: str) -> Job | None:
        """Return a job by identifier."""
        ...