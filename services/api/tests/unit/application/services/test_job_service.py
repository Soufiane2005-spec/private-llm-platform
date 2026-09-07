from application.services.job_service import (
    ORPHANED_RUNNING_JOB_ERROR,
    JobService,
    fail_orphaned_running_jobs,
)
from domain.jobs.job import Job, JobStatus
from infrastructure.persistence.in_memory_job_repository import (
    InMemoryJobRepository,
)
from infrastructure.queue.in_memory_dead_letter_queue import (
    InMemoryDeadLetterQueue,
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


def test_service_exposes_queue_and_dead_letter_counts() -> None:
    queue = InMemoryJobQueue()
    dead_letter_queue = InMemoryDeadLetterQueue()
    service = JobService(
        queue=queue,
        repository=InMemoryJobRepository(),
        dead_letter_queue=dead_letter_queue,
    )

    service.submit("benchmark")

    assert service.queue_size() == 1
    assert service.dead_letter_size() == 0
    assert service.list_dead_letters() == ()


def test_service_run_once_completes_next_job() -> None:
    service = JobService(
        queue=InMemoryJobQueue(),
        repository=InMemoryJobRepository(),
        dead_letter_queue=InMemoryDeadLetterQueue(),
    )
    job = service.submit("benchmark")

    result = service.run_once()

    assert result is not None
    assert result.job_id == job.job_id
    assert result.status is JobStatus.COMPLETED
    assert service.queue_size() == 0


def test_service_run_once_records_dead_letter_after_permanent_failure() -> None:
    service = JobService(
        queue=InMemoryJobQueue(),
        repository=InMemoryJobRepository(),
        dead_letter_queue=InMemoryDeadLetterQueue(),
        handler=lambda job: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    service.submit("benchmark", max_attempts=1)

    result = service.run_once()

    assert result is not None
    assert result.status is JobStatus.FAILED
    assert service.dead_letter_size() == 1
    assert service.list_dead_letters() == (result,)


def test_service_run_once_requires_dead_letter_queue() -> None:
    service = JobService(
        queue=InMemoryJobQueue(),
        repository=InMemoryJobRepository(),
    )

    try:
        service.run_once()
    except RuntimeError as exc:
        assert str(exc) == "dead letter queue is required to run jobs."
    else:
        raise AssertionError("Expected RuntimeError when worker has no DLQ.")


def test_fail_orphaned_running_jobs_marks_only_running_jobs_failed() -> None:
    repository = InMemoryJobRepository()
    pending = Job(job_id="pending", job_type="benchmark")
    running = Job(job_id="running", job_type="benchmark").mark_running()
    completed = Job(job_id="completed", job_type="benchmark").mark_running()
    completed = completed.mark_completed()

    repository.save(pending)
    repository.save(running)
    repository.save(completed)

    failed = fail_orphaned_running_jobs(repository)

    assert [job.job_id for job in failed] == ["running"]
    assert repository.get("pending").status is JobStatus.PENDING
    assert repository.get("completed").status is JobStatus.COMPLETED
    assert repository.get("running").status is JobStatus.FAILED
    assert repository.get("running").error == ORPHANED_RUNNING_JOB_ERROR
