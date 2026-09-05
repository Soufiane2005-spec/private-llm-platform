"""In-memory dead letter queue implementation."""

from collections import deque

from domain.jobs.job import Job


class InMemoryDeadLetterQueue:
    """FIFO storage for permanently failed jobs."""

    def __init__(self) -> None:
        self._jobs: deque[Job] = deque()

    def add(self, job: Job) -> None:
        """Add a failed job to the dead letter queue."""
        self._jobs.append(job)

    def get_next(self) -> Job | None:
        """Retrieve and remove the oldest failed job."""

        if not self._jobs:
            return None

        return self._jobs.popleft()

    def list(self) -> tuple[Job, ...]:
        """Return failed jobs without removing them."""
        return tuple(self._jobs)

    def size(self) -> int:
        """Return the number of dead-lettered jobs."""
        return len(self._jobs)
