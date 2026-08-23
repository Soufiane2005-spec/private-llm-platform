"""Application port for dead letter queues."""

from typing import Protocol

from domain.jobs.job import Job


class DeadLetterQueue(Protocol):
    """Storage contract for permanently failed jobs."""

    def add(self, job: Job) -> None:
        """Add a permanently failed job."""
        ...

    def get_next(self) -> Job | None:
        """Retrieve and remove the oldest dead-lettered job."""
        ...

    def size(self) -> int:
        """Return the number of dead-lettered jobs."""
        ...