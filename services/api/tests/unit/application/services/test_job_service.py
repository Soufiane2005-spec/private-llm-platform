from application.services.job_service import JobService
from domain.jobs.job import JobStatus
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue


def test_submit_creates_pending_job() -> None:
    queue = InMemoryJobQueue()
    service = JobService(queue)

    job = service.submit("inference")

    assert job.job_id
    assert job.job_type == "inference"
    assert job.status is JobStatus.PENDING


def test_submit_enqueues_job() -> None:
    queue = InMemoryJobQueue()
    service = JobService(queue)

    job = service.submit("benchmark")

    assert queue.size() == 1
    assert queue.dequeue() == job