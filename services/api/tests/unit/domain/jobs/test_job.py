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