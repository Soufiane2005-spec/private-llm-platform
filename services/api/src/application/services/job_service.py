"""Application service for asynchronous jobs."""

from collections.abc import Callable
from uuid import uuid4

from application.ports.dead_letter_queue import DeadLetterQueue
from application.ports.job_queue import JobQueue
from application.ports.job_repository import JobRepository
from application.services.job_worker import JobWorker
from domain.jobs.job import Job


def _default_job_handler(job: Job) -> None:
    """Complete demo jobs without side effects."""


class JobService:
    """Create, submit, and retrieve asynchronous jobs."""

    def __init__(
        self,
        queue: JobQueue,
        repository: JobRepository,
        dead_letter_queue: DeadLetterQueue | None = None,
        handler: Callable[[Job], None] = _default_job_handler,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._queue = queue
        self._repository = repository
        self._dead_letter_queue = dead_letter_queue
        self._handler = handler
        self._timeout_seconds = timeout_seconds

    def submit(self, job_type: str, *, max_attempts: int = 3) -> Job:
        """Create, persist, and enqueue a pending job."""

        clean_job_type = job_type.strip()

        if not clean_job_type:
            raise ValueError("job_type cannot be empty.")

        job = Job(
            job_id=str(uuid4()),
            job_type=clean_job_type,
            max_attempts=max_attempts,
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

    def queue_size(self) -> int:
        """Return queued job count."""

        return self._queue.size()

    def dead_letter_size(self) -> int:
        """Return dead-lettered job count."""

        if self._dead_letter_queue is None:
            return 0

        return self._dead_letter_queue.size()

    def list_dead_letters(self) -> tuple[Job, ...]:
        """Return permanently failed jobs held by the dead letter queue."""

        if self._dead_letter_queue is None:
            return ()

        return self._dead_letter_queue.list()

    def run_once(self) -> Job | None:
        """Run the next queued job through the worker."""

        if self._dead_letter_queue is None:
            raise RuntimeError("dead letter queue is required to run jobs.")

        worker = JobWorker(
            queue=self._queue,
            repository=self._repository,
            dead_letter_queue=self._dead_letter_queue,
            handler=self._handler,
            timeout_seconds=self._timeout_seconds,
        )

        return worker.run_once()
