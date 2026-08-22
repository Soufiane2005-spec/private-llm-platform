"""Application worker for asynchronous jobs."""

from collections.abc import Callable

from application.ports.job_queue import JobQueue
from domain.jobs.job import Job


class JobWorker:
    """Consume and execute jobs from a queue."""

    def __init__(
        self,
        queue: JobQueue,
        handler: Callable[[Job], None],
    ) -> None:
        self._queue = queue
        self._handler = handler

    def run_once(self) -> Job | None:
        """Consume and execute one job."""

        job = self._queue.dequeue()

        if job is None:
            return None

        running_job = job.mark_running()

        try:
            self._handler(running_job)
        except Exception as exc:
            return running_job.mark_failed(str(exc))

        return running_job.mark_completed()