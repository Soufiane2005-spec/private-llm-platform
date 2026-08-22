"""Application port for asynchronous job queues."""

from typing import Protocol

from domain.jobs.job import Job


class JobQueue(Protocol):
    """Interface for job queue implementations."""

    def enqueue(self, job: Job) -> None:
        """Add a job to the queue."""
        ...

    def dequeue(self) -> Job | None:
        """Retrieve the next job from the queue."""
        ...

    def size(self) -> int:
        """Return the number of queued jobs."""
        ...