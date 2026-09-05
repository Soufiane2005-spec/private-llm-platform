from domain.jobs.job import Job, JobStatus
from infrastructure.queue.in_memory_dead_letter_queue import (
    InMemoryDeadLetterQueue,
)


def create_failed_job(job_id: str = "job-1") -> Job:
    return Job(
        job_id=job_id,
        job_type="inference",
        status=JobStatus.FAILED,
        error="execution failed",
        attempts=3,
        max_attempts=3,
    )


def test_dead_letter_queue_starts_empty() -> None:
    queue = InMemoryDeadLetterQueue()

    assert queue.size() == 0
    assert queue.get_next() is None


def test_dead_letter_queue_adds_failed_job() -> None:
    queue = InMemoryDeadLetterQueue()
    job = create_failed_job()

    queue.add(job)

    assert queue.size() == 1
    assert queue.list() == (job,)
    assert queue.get_next() == job
    assert queue.size() == 0


def test_dead_letter_queue_is_fifo() -> None:
    queue = InMemoryDeadLetterQueue()

    first = create_failed_job("job-1")
    second = create_failed_job("job-2")

    queue.add(first)
    queue.add(second)

    assert queue.list() == (first, second)
    assert queue.get_next() == first
    assert queue.get_next() == second
    assert queue.get_next() is None
