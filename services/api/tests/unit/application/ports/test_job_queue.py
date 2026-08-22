from application.ports.job_queue import JobQueue
from domain.jobs.job import Job


def test_job_queue_protocol_exists() -> None:
    assert JobQueue is not None


def test_job_model_can_be_used_by_queue() -> None:
    job = Job(
        job_id="job-1",
        job_type="inference",
    )

    assert job.job_id == "job-1"