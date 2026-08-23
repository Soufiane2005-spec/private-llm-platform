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
    assert job.attempts == 0
    assert job.max_attempts == 3


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


def test_register_attempt_increments_attempt_count() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
    )

    attempted = job.register_attempt()

    assert attempted.attempts == 1
    assert job.attempts == 0


def test_job_can_retry_before_max_attempts() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
        attempts=1,
        max_attempts=3,
    )

    assert job.can_retry is True


def test_job_cannot_retry_after_max_attempts() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
        attempts=3,
        max_attempts=3,
    )

    assert job.can_retry is False


def test_register_attempt_rejects_maximum_attempts() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
        attempts=3,
        max_attempts=3,
    )

    with pytest.raises(
        ValueError,
        match="maximum job attempts reached",
    ):
        job.register_attempt()


def test_reject_negative_attempts() -> None:
    with pytest.raises(
        ValueError,
        match="attempts cannot be negative",
    ):
        Job(
            job_id="job-1",
            job_type="inference",
            attempts=-1,
        )


def test_reject_non_positive_max_attempts() -> None:
    with pytest.raises(
        ValueError,
        match="max_attempts must be greater than zero",
    ):
        Job(
            job_id="job-1",
            job_type="inference",
            max_attempts=0,
        )


def test_reject_attempts_greater_than_max_attempts() -> None:
    with pytest.raises(
        ValueError,
        match="attempts cannot exceed max_attempts",
    ):
        Job(
            job_id="job-1",
            job_type="inference",
            attempts=4,
            max_attempts=3,
        )
def test_running_job_can_return_to_pending_for_retry() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
        status=JobStatus.RUNNING,
        attempts=1,
        max_attempts=3,
    )

    retry_job = job.mark_retry_pending()

    assert retry_job.status is JobStatus.PENDING
    assert retry_job.attempts == 1
    assert retry_job.error is None


def test_job_cannot_return_to_pending_when_retries_exhausted() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
        status=JobStatus.RUNNING,
        attempts=3,
        max_attempts=3,
    )

    with pytest.raises(
        ValueError,
        match="job has no retry attempts remaining",
    ):
        job.mark_retry_pending()