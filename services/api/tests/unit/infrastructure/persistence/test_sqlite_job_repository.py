"""Tests for SQLite job persistence."""

from domain.jobs.job import Job, JobStatus
from infrastructure.persistence.sqlite_job_repository import SQLiteJobRepository


def test_sqlite_job_repository_persists_jobs(tmp_path) -> None:
    """Jobs survive repository re-creation."""

    database_path = tmp_path / "platform.db"
    repository = SQLiteJobRepository(database_path)
    job = Job(
        job_id="job-1",
        job_type="deploy-model",
        status=JobStatus.RUNNING,
        attempts=1,
    )

    repository.save(job)

    reloaded = SQLiteJobRepository(database_path)

    assert reloaded.get("job-1") == job


def test_sqlite_job_repository_replaces_and_lists_jobs(tmp_path) -> None:
    """Jobs are ordered and replaceable."""

    repository = SQLiteJobRepository(tmp_path / "platform.db")
    repository.save(Job(job_id="job-b", job_type="benchmark"))
    repository.save(Job(job_id="job-a", job_type="deploy"))
    repository.save(
        Job(
            job_id="job-a",
            job_type="deploy",
            status=JobStatus.FAILED,
            error="failed",
        )
    )

    jobs = repository.list()

    assert [job.job_id for job in jobs] == ["job-a", "job-b"]
    assert jobs[0].status is JobStatus.FAILED
