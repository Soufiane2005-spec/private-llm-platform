"""Application service for asynchronous jobs."""

from uuid import uuid4

from application.ports.job_queue import JobQueue
from domain.jobs.job import Job


class JobService:
    """Create and submit asynchronous jobs."""

    def __init__(self, queue: JobQueue) -> None:
        self._queue = queue

    def submit(self, job_type: str) -> Job:
        """Create a pending job and enqueue it."""

        job = Job(
            job_id=str(uuid4()),
            job_type=job_type,
        )

        self._queue.enqueue(job)

        return job