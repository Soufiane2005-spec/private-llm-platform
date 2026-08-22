from domain.jobs.job import Job, JobStatus
from infrastructure.persistence.in_memory_job_repository import (
    InMemoryJobRepository,
)


def test_repository_returns_none_for_unknown_job() -> None:
    repository = InMemoryJobRepository()

    assert repository.get("missing") is None


def test_repository_saves_job() -> None:
    repository = InMemoryJobRepository()
    job = Job(job_id="job-1", job_type="inference")

    repository.save(job)

    assert repository.get("job-1") == job


def test_repository_replaces_existing_job_state() -> None:
    repository = InMemoryJobRepository()

    pending = Job(
        job_id="job-1",
        job_type="inference",
    )

    running = Job(
        job_id="job-1",
        job_type="inference",
        status=JobStatus.RUNNING,
    )

    repository.save(pending)
    repository.save(running)

    assert repository.get("job-1") == running