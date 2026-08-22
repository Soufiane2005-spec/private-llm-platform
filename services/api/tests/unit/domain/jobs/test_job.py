import pytest

from domain.jobs.job import Job, JobStatus


def test_create_pending_job() -> None:
    job = Job(
        job_id="job-123",
        job_type="inference",
    )

    assert job.job_id == "job-123"
    assert job.status is JobStatus.PENDING
    assert job.error is None


def test_create_failed_job_with_error() -> None:
    job = Job(
        job_id="job-123",
        job_type="benchmark",
        status=JobStatus.FAILED,
        error="engine unavailable",
    )

    assert job.status is JobStatus.FAILED
    assert job.error == "engine unavailable"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("job_id", ""),
        ("job_type", ""),
    ],
)
def test_reject_empty_required_fields(
    field: str,
    value: str,
) -> None:
    values = {
        "job_id": "job-123",
        "job_type": "inference",
    }
    values[field] = value

    with pytest.raises(ValueError):
        Job(**values)


def test_failed_job_requires_error() -> None:
    with pytest.raises(
        ValueError,
        match="failed jobs must contain an error",
    ):
        Job(
            job_id="job-123",
            job_type="benchmark",
            status=JobStatus.FAILED,
        )
def test_pending_job_can_start_running() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
    )

    running = job.mark_running()

    assert running.status is JobStatus.RUNNING
    assert job.status is JobStatus.PENDING


def test_running_job_can_complete() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
        status=JobStatus.RUNNING,
    )

    completed = job.mark_completed()

    assert completed.status is JobStatus.COMPLETED


def test_running_job_can_fail() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
        status=JobStatus.RUNNING,
    )

    failed = job.mark_failed("model unavailable")

    assert failed.status is JobStatus.FAILED
    assert failed.error == "model unavailable"


def test_pending_job_cannot_complete() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
    )

    with pytest.raises(
        ValueError,
        match="only running jobs can complete",
    ):
        job.mark_completed()