from application.services.job_worker import JobWorker
from domain.jobs.job import Job, JobStatus
from infrastructure.persistence.in_memory_job_repository import (
    InMemoryJobRepository,
)
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue


def test_worker_returns_none_when_queue_is_empty() -> None:
    worker = JobWorker(
        InMemoryJobQueue(),
        InMemoryJobRepository(),
        lambda job: None,
    )

    assert worker.run_once() is None


def test_worker_persists_completed_job() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()

    job = Job(
        job_id="job-1",
        job_type="inference",
    )
    queue.enqueue(job)
    repository.save(job)

    worker = JobWorker(
        queue,
        repository,
        lambda job: None,
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.COMPLETED
    assert repository.get(job.job_id) == result


def test_worker_persists_failed_job() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()

    job = Job(
        job_id="job-1",
        job_type="inference",
    )
    queue.enqueue(job)
    repository.save(job)

    def failing_handler(job: Job) -> None:
        raise RuntimeError("model execution failed")

    worker = JobWorker(
        queue,
        repository,
        failing_handler,
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.FAILED
    assert result.error == "model execution failed"
    assert repository.get(job.job_id) == result