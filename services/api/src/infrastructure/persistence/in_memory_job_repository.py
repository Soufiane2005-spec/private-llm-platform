"""In-memory job repository implementation."""

from domain.jobs.job import Job


class InMemoryJobRepository:
    """Store jobs in memory by identifier."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def save(self, job: Job) -> None:
        """Store or replace a job."""
        self._jobs[job.job_id] = job

    def get(self, job_id: str) -> Job | None:
        """Return a job by identifier."""
        return self._jobs.get(job_id)
    def list(self) -> tuple[Job, ...]:
        """Return all jobs in deterministic order."""
        return tuple(
        self._jobs[job_id]
        for job_id in sorted(self._jobs)
    )