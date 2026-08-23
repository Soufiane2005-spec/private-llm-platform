"""Application worker for asynchronous jobs."""

from collections.abc import Callable

from application.ports.job_queue import JobQueue
from application.ports.job_repository import JobRepository
from domain.jobs.job import Job


class JobWorker:
    """Consume, execute, retry, and persist jobs from a queue."""

    def __init__(
        self,
        queue: JobQueue,
        repository: JobRepository,
        handler: Callable[[Job], None],
    ) -> None:
        self._queue = queue
        self._repository = repository
        self._handler = handler

    def run_once(self) -> Job | None:
        """Consume and execute one job."""

        job = self._queue.dequeue()

        if job is None:
            return None

        attempted_job = job.register_attempt()
        running_job = attempted_job.mark_running()

        self._repository.save(running_job)

        try:
            self._handler(running_job)
        except Exception as exc:
            if running_job.can_retry:
                retry_job = running_job.mark_retry_pending()

                self._repository.save(retry_job)
                self._queue.enqueue(retry_job)

                return retry_job

            failed_job = running_job.mark_failed(str(exc))
            self._repository.save(failed_job)

            return failed_job

        completed_job = running_job.mark_completed()
        self._repository.save(completed_job)

        return completed_job