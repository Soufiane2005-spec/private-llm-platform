import time

import pytest

from application.services.job_worker import JobWorker
from domain.jobs.job import Job, JobStatus
from infrastructure.persistence.in_memory_job_repository import (
    InMemoryJobRepository,
)
from infrastructure.queue.in_memory_dead_letter_queue import (
    InMemoryDeadLetterQueue,
)
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue


def test_worker_returns_none_when_queue_is_empty() -> None:
    worker = JobWorker(
        InMemoryJobQueue(),
        InMemoryJobRepository(),
        InMemoryDeadLetterQueue(),
        lambda job: None,
    )

    assert worker.run_once() is None


def test_worker_completes_successful_job() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    dead_letter_queue = InMemoryDeadLetterQueue()

    job = Job(
        job_id="job-1",
        job_type="inference",
    )

    queue.enqueue(job)
    repository.save(job)

    worker = JobWorker(
        queue,
        repository,
        dead_letter_queue,
        lambda job: None,
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.COMPLETED
    assert result.attempts == 1
    assert repository.get(job.job_id) == result
    assert queue.size() == 0
    assert dead_letter_queue.size() == 0


def test_worker_requeues_failed_job_when_retry_available() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    dead_letter_queue = InMemoryDeadLetterQueue()

    job = Job(
        job_id="job-1",
        job_type="inference",
        max_attempts=3,
    )

    queue.enqueue(job)
    repository.save(job)

    def failing_handler(job: Job) -> None:
        raise RuntimeError("model execution failed")

    worker = JobWorker(
        queue,
        repository,
        dead_letter_queue,
        failing_handler,
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.PENDING
    assert result.attempts == 1
    assert result.can_retry is True

    assert repository.get(job.job_id) == result
    assert queue.size() == 1
    assert dead_letter_queue.size() == 0

    assert queue.dequeue() == result


def test_worker_marks_job_failed_after_last_attempt() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    dead_letter_queue = InMemoryDeadLetterQueue()

    job = Job(
        job_id="job-1",
        job_type="inference",
        max_attempts=1,
    )

    queue.enqueue(job)
    repository.save(job)

    def failing_handler(job: Job) -> None:
        raise RuntimeError("model execution failed")

    worker = JobWorker(
        queue,
        repository,
        dead_letter_queue,
        failing_handler,
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.FAILED
    assert result.error == "model execution failed"
    assert result.attempts == 1
    assert result.can_retry is False

    assert repository.get(job.job_id) == result
    assert queue.size() == 0

    assert dead_letter_queue.size() == 1
    assert dead_letter_queue.get_next() == result


def test_worker_can_retry_then_complete_job() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    dead_letter_queue = InMemoryDeadLetterQueue()

    job = Job(
        job_id="job-1",
        job_type="inference",
        max_attempts=3,
    )

    queue.enqueue(job)
    repository.save(job)

    calls = 0

    def flaky_handler(job: Job) -> None:
        nonlocal calls
        calls += 1

        if calls == 1:
            raise RuntimeError("temporary failure")

    worker = JobWorker(
        queue,
        repository,
        dead_letter_queue,
        flaky_handler,
    )

    first_result = worker.run_once()

    assert first_result is not None
    assert first_result.status is JobStatus.PENDING
    assert first_result.attempts == 1
    assert queue.size() == 1
    assert dead_letter_queue.size() == 0

    second_result = worker.run_once()

    assert second_result is not None
    assert second_result.status is JobStatus.COMPLETED
    assert second_result.attempts == 2
    assert second_result.error is None

    assert repository.get(job.job_id) == second_result
    assert queue.size() == 0
    assert dead_letter_queue.size() == 0


def test_worker_requeues_timed_out_job_when_retry_available() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    dead_letter_queue = InMemoryDeadLetterQueue()

    job = Job(
        job_id="job-timeout",
        job_type="inference",
        max_attempts=3,
    )

    queue.enqueue(job)
    repository.save(job)

    def slow_handler(job: Job) -> None:
        time.sleep(0.1)

    worker = JobWorker(
        queue,
        repository,
        dead_letter_queue,
        slow_handler,
        timeout_seconds=0.01,
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.PENDING
    assert result.attempts == 1

    assert repository.get(job.job_id) == result
    assert queue.size() == 1
    assert dead_letter_queue.size() == 0


def test_worker_marks_timed_out_job_failed_on_last_attempt() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    dead_letter_queue = InMemoryDeadLetterQueue()

    job = Job(
        job_id="job-timeout",
        job_type="inference",
        max_attempts=1,
    )

    queue.enqueue(job)
    repository.save(job)

    def slow_handler(job: Job) -> None:
        time.sleep(0.1)

    worker = JobWorker(
        queue,
        repository,
        dead_letter_queue,
        slow_handler,
        timeout_seconds=0.01,
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.FAILED
    assert result.attempts == 1
    assert result.error is not None
    assert "exceeded timeout" in result.error

    assert queue.size() == 0
    assert repository.get(job.job_id) == result

    assert dead_letter_queue.size() == 1
    assert dead_letter_queue.get_next() == result


def test_worker_rejects_non_positive_timeout() -> None:
    with pytest.raises(
        ValueError,
        match="timeout_seconds must be greater than zero",
    ):
        JobWorker(
            InMemoryJobQueue(),
            InMemoryJobRepository(),
            InMemoryDeadLetterQueue(),
            lambda job: None,
            timeout_seconds=0,
        )


def test_worker_sends_permanently_failed_job_to_dead_letter_queue() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    dead_letter_queue = InMemoryDeadLetterQueue()

    job = Job(
        job_id="job-dead",
        job_type="inference",
        max_attempts=1,
    )

    queue.enqueue(job)
    repository.save(job)

    def failing_handler(job: Job) -> None:
        raise RuntimeError("permanent execution failure")

    worker = JobWorker(
        queue,
        repository,
        dead_letter_queue,
        failing_handler,
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.FAILED
    assert result.attempts == 1
    assert result.error == "permanent execution failure"

    assert repository.get(job.job_id) == result
    assert queue.size() == 0

    assert dead_letter_queue.size() == 1
    assert dead_letter_queue.get_next() == result


def test_worker_does_not_dead_letter_job_when_retry_is_available() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    dead_letter_queue = InMemoryDeadLetterQueue()

    job = Job(
        job_id="job-retry",
        job_type="inference",
        max_attempts=3,
    )

    queue.enqueue(job)
    repository.save(job)

    def failing_handler(job: Job) -> None:
        raise RuntimeError("temporary failure")

    worker = JobWorker(
        queue,
        repository,
        dead_letter_queue,
        failing_handler,
    )

    result = worker.run_once()

    assert result is not None
    assert result.status is JobStatus.PENDING
    assert result.attempts == 1

    assert queue.size() == 1
    assert dead_letter_queue.size() == 0