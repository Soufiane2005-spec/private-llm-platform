from application.services.job_service import JobService
from domain.jobs.job import Job, JobStatus
from infrastructure.persistence.in_memory_job_repository import (
    InMemoryJobRepository,
)
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue


def test_list_jobs_returns_repository_jobs() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    service = JobService(queue=queue, repository=repository)

    first = Job(job_id="job-a", job_type="inference")
    second = Job(job_id="job-b", job_type="benchmark")

    repository.save(first)
    repository.save(second)

    assert service.list_jobs() == (first, second)


def test_submit_creates_and_persists_pending_job() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    service = JobService(queue, repository)

    job = service.submit(" inference ")

    assert job.job_id
    assert job.job_type == "inference"
    assert job.status is JobStatus.PENDING
    assert repository.get(job.job_id) == job


def test_submit_enqueues_job() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    service = JobService(queue, repository)

    job = service.submit("benchmark")

    assert queue.size() == 1
    assert queue.dequeue() == job


def test_get_returns_persisted_job() -> None:
    queue = InMemoryJobQueue()
    repository = InMemoryJobRepository()
    service = JobService(queue, repository)

    job = service.submit("inference")

    assert service.get(job.job_id) == job


def test_submit_rejects_empty_job_type() -> None:
    service = JobService(
        InMemoryJobQueue(),
        InMemoryJobRepository(),
    )

    try:
        service.submit("   ")
    except ValueError as exc:
        assert str(exc) == "job_type cannot be empty."
    else:
        raise AssertionError("Expected ValueError for blank job type.")


def test_get_returns_none_for_unknown_job() -> None:
    service = JobService(
        InMemoryJobQueue(),
        InMemoryJobRepository(),
    )

    assert service.get("missing") is None
