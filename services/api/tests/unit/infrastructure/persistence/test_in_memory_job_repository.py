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
def test_list_returns_jobs_in_deterministic_order() -> None:
    repository = InMemoryJobRepository()

    repository.save(Job(job_id="job-b", job_type="benchmark"))
    repository.save(Job(job_id="job-a", job_type="inference"))

    jobs = repository.list()

    assert [job.job_id for job in jobs] == ["job-a", "job-b"]