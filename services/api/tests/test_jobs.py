"""HTTP tests for asynchronous job endpoints."""

from fastapi.testclient import TestClient

from application.services.job_service import JobService
from domain.jobs.job import Job
from infrastructure.persistence.in_memory_job_repository import (
    InMemoryJobRepository,
)
from infrastructure.queue.in_memory_dead_letter_queue import (
    InMemoryDeadLetterQueue,
)
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue
from interfaces.http.app import create_app
from interfaces.http.routes.jobs import get_job_service


def create_test_client(
    repository: InMemoryJobRepository,
    service: JobService | None = None,
) -> TestClient:
    """Create a client using an isolated job repository."""

    if service is None:
        service = JobService(
            queue=InMemoryJobQueue(),
            repository=repository,
            dead_letter_queue=InMemoryDeadLetterQueue(),
        )

    app = create_app()
    app.dependency_overrides[get_job_service] = lambda: service

    return TestClient(app)


def test_list_jobs_returns_empty_list() -> None:
    """Return an empty list when no jobs exist."""

    repository = InMemoryJobRepository()
    client = create_test_client(repository)

    response = client.get("/jobs")

    assert response.status_code == 200
    assert response.json() == []


def test_list_jobs_returns_tracked_jobs() -> None:
    """Return all tracked jobs."""

    repository = InMemoryJobRepository()

    repository.save(
        Job(
            job_id="job-1",
            job_type="benchmark",
        )
    )

    repository.save(
        Job(
            job_id="job-2",
            job_type="inference",
        )
    )

    client = create_test_client(repository)

    response = client.get("/jobs")

    assert response.status_code == 200
    assert response.json() == [
        {
            "job_id": "job-1",
            "job_type": "benchmark",
            "status": "pending",
            "error": None,
            "attempts": 0,
            "max_attempts": 3,
        },
        {
            "job_id": "job-2",
            "job_type": "inference",
            "status": "pending",
            "error": None,
            "attempts": 0,
            "max_attempts": 3,
        },
    ]


def test_submit_job_creates_pending_job() -> None:
    """Submit a new asynchronous job through the HTTP API."""

    repository = InMemoryJobRepository()
    client = create_test_client(repository)

    response = client.post(
        "/jobs",
        json={"job_type": " benchmark "},
    )

    assert response.status_code == 201

    body = response.json()

    assert body["job_id"]
    assert body["job_type"] == "benchmark"
    assert body["status"] == "pending"
    assert body["error"] is None
    assert body["attempts"] == 0
    assert body["max_attempts"] == 3
    assert repository.get(body["job_id"]) is not None


def test_submit_job_accepts_custom_max_attempts() -> None:
    """Submit a job with an explicit retry budget."""

    repository = InMemoryJobRepository()
    client = create_test_client(repository)

    response = client.post(
        "/jobs",
        json={"job_type": "benchmark", "max_attempts": 5},
    )

    assert response.status_code == 201
    assert response.json()["max_attempts"] == 5


def test_submit_job_rejects_blank_type() -> None:
    """Reject a blank asynchronous job type."""

    repository = InMemoryJobRepository()
    client = create_test_client(repository)

    response = client.post(
        "/jobs",
        json={"job_type": "   "},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "job_type cannot be empty.",
    }


def test_get_job_returns_job() -> None:
    """Return a tracked job by identifier."""

    repository = InMemoryJobRepository()

    repository.save(
        Job(
            job_id="job-1",
            job_type="benchmark",
        )
    )

    client = create_test_client(repository)

    response = client.get("/jobs/job-1")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-1",
        "job_type": "benchmark",
        "status": "pending",
        "error": None,
        "attempts": 0,
        "max_attempts": 3,
    }


def test_get_job_returns_404_for_unknown_job() -> None:
    """Return 404 when a job does not exist."""

    repository = InMemoryJobRepository()
    client = create_test_client(repository)

    response = client.get("/jobs/unknown-job")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Job not found.",
    }


def test_job_runtime_returns_queue_and_dead_letter_counts() -> None:
    """Return runtime counters for queued and dead-lettered jobs."""

    repository = InMemoryJobRepository()
    client = create_test_client(repository)

    client.post("/jobs", json={"job_type": "benchmark"})

    response = client.get("/jobs/runtime")

    assert response.status_code == 200
    assert response.json() == {
        "queue_size": 1,
        "dead_letter_size": 0,
    }


def test_run_next_job_completes_pending_job() -> None:
    """Run one queued job through the local worker."""

    repository = InMemoryJobRepository()
    client = create_test_client(repository)
    created = client.post("/jobs", json={"job_type": "benchmark"}).json()

    response = client.post("/jobs/run-next")

    assert response.status_code == 200
    body = response.json()
    assert body["job"]["job_id"] == created["job_id"]
    assert body["job"]["status"] == "completed"
    assert body["runtime"] == {
        "queue_size": 0,
        "dead_letter_size": 0,
    }


def test_run_next_job_returns_null_when_queue_is_empty() -> None:
    """Return an empty worker result when no queued job is available."""

    repository = InMemoryJobRepository()
    client = create_test_client(repository)

    response = client.post("/jobs/run-next")

    assert response.status_code == 200
    assert response.json() == {
        "job": None,
        "runtime": {
            "queue_size": 0,
            "dead_letter_size": 0,
        },
    }


def test_dead_letter_endpoint_returns_permanently_failed_jobs() -> None:
    """Expose dead-lettered jobs without removing them."""

    repository = InMemoryJobRepository()
    service = JobService(
        queue=InMemoryJobQueue(),
        repository=repository,
        dead_letter_queue=InMemoryDeadLetterQueue(),
        handler=lambda job: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    client = create_test_client(repository, service=service)
    created = client.post(
        "/jobs",
        json={"job_type": "benchmark", "max_attempts": 1},
    ).json()

    client.post("/jobs/run-next")
    response = client.get("/jobs/dead-letter")

    assert response.status_code == 200
    assert response.json()[0]["job_id"] == created["job_id"]
    assert response.json()[0]["status"] == "failed"
    assert response.json()[0]["error"] == "boom"
