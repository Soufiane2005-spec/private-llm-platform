import pytest

from application.services.job_worker import JobWorker
from domain.jobs.job import Job, JobStatus
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue


def test_worker_returns_none_when_queue_is_empty() -> None:
    queue = InMemoryJobQueue()
    worker = JobWorker(queue, lambda job: None)

    assert worker.run_once() is None


def test_worker_completes_job() -> None:
    queue = InMemoryJobQueue()

    job = Job(
        job_id="job-1",
        job_type="inference",
    )
    queue.enqueue(job)

    worker = JobWorker(queue, lambda job: None)

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.COMPLETED


def test_worker_marks_job_failed_when_handler_raises() -> None:
    queue = InMemoryJobQueue()

    job = Job(
        job_id="job-1",
        job_type="inference",
    )
    queue.enqueue(job)

    def failing_handler(job: Job) -> None:
        raise RuntimeError("model execution failed")

    worker = JobWorker(queue, failing_handler)

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.FAILED
    assert result.error == "model execution failed"