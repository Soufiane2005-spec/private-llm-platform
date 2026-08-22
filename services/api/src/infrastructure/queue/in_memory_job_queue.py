"""In-memory implementation of the job queue."""

from collections import deque

from domain.jobs.job import Job


class InMemoryJobQueue:
    """FIFO job queue stored in application memory."""

    def __init__(self) -> None:
        self._jobs: deque[Job] = deque()

    def enqueue(self, job: Job) -> None:
        """Add a job to the end of the queue."""
        self._jobs.append(job)

    def dequeue(self) -> Job | None:
        """Retrieve and remove the oldest queued job."""
        if not self._jobs:
            return None

        return self._jobs.popleft()

    def size(self) -> int:
        """Return the number of queued jobs."""
        return len(self._jobs)