from domain.jobs.job import Job
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue


def test_queue_starts_empty() -> None:
    queue = InMemoryJobQueue()

    assert queue.size() == 0
    assert queue.dequeue() is None


def test_enqueue_job() -> None:
    queue = InMemoryJobQueue()
    job = Job(job_id="job-1", job_type="inference")

    queue.enqueue(job)

    assert queue.size() == 1


def test_dequeue_job() -> None:
    queue = InMemoryJobQueue()
    job = Job(job_id="job-1", job_type="inference")

    queue.enqueue(job)

    result = queue.dequeue()

    assert result == job
    assert queue.size() == 0


def test_queue_is_fifo() -> None:
    queue = InMemoryJobQueue()

    first = Job(job_id="job-1", job_type="inference")
    second = Job(job_id="job-2", job_type="benchmark")

    queue.enqueue(first)
    queue.enqueue(second)

    assert queue.dequeue() == first
    assert queue.dequeue() == second
    assert queue.dequeue() is None