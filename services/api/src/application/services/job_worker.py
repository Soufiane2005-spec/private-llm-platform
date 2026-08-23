"""Application worker for asynchronous jobs."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

from application.ports.dead_letter_queue import DeadLetterQueue
from application.ports.job_queue import JobQueue
from application.ports.job_repository import JobRepository
from domain.jobs.job import Job


class JobTimeoutError(RuntimeError):
    """Raised when a job execution exceeds its timeout."""


class JobWorker:
    """Consume, execute, retry, timeout, and dead-letter jobs."""

    def __init__(
        self,
        queue: JobQueue,
        repository: JobRepository,
        dead_letter_queue: DeadLetterQueue,
        handler: Callable[[Job], None],
        timeout_seconds: float = 30.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")

        self._queue = queue
        self._repository = repository
        self._dead_letter_queue = dead_letter_queue
        self._handler = handler
        self._timeout_seconds = timeout_seconds

    def run_once(self) -> Job | None:
        """Consume and execute one job."""

        job = self._queue.dequeue()

        if job is None:
            return None

        attempted_job = job.register_attempt()
        running_job = attempted_job.mark_running()

        self._repository.save(running_job)

        try:
            self._execute_with_timeout(running_job)

        except Exception as exc:
            if running_job.can_retry:
                retry_job = running_job.mark_retry_pending()

                self._repository.save(retry_job)
                self._queue.enqueue(retry_job)

                return retry_job

            failed_job = running_job.mark_failed(str(exc))

            self._repository.save(failed_job)
            self._dead_letter_queue.add(failed_job)

            return failed_job

        completed_job = running_job.mark_completed()
        self._repository.save(completed_job)

        return completed_job

    def _execute_with_timeout(self, job: Job) -> None:
        """Execute a job handler with a timeout."""

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._handler, job)

        try:
            future.result(timeout=self._timeout_seconds)

        except FuturesTimeoutError as exc:
            future.cancel()

            raise JobTimeoutError(
                f"job execution exceeded timeout of "
                f"{self._timeout_seconds} seconds"
            ) from exc

        finally:
            executor.shutdown(
                wait=False,
                cancel_futures=True,
            )