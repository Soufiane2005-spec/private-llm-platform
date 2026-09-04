"""Application service for asynchronous jobs."""

from uuid import uuid4

from application.ports.job_queue import JobQueue
from application.ports.job_repository import JobRepository
from domain.jobs.job import Job


class JobService:
    """Create, submit, and retrieve asynchronous jobs."""

    def __init__(
        self,
        queue: JobQueue,
        repository: JobRepository,
    ) -> None:
        self._queue = queue
        self._repository = repository

    def submit(self, job_type: str) -> Job:
        """Create, persist, and enqueue a pending job."""

        clean_job_type = job_type.strip()

        if not clean_job_type:
            raise ValueError("job_type cannot be empty.")

        job = Job(
            job_id=str(uuid4()),
            job_type=clean_job_type,
        )

        self._repository.save(job)
        self._queue.enqueue(job)

        return job

    def get(self, job_id: str) -> Job | None:
        """Return a job by identifier."""

        return self._repository.get(job_id)

    def list_jobs(self) -> tuple[Job, ...]:
        """Return all tracked jobs."""

        return self._repository.list()
