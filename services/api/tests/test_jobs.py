"""HTTP tests for asynchronous job endpoints."""

from fastapi.testclient import TestClient

from application.services.job_service import JobService
from domain.jobs.job import Job
from infrastructure.persistence.in_memory_job_repository import (
    InMemoryJobRepository,
)
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue
from interfaces.http.app import create_app
from interfaces.http.routes.jobs import get_job_service


def create_test_client(
    repository: InMemoryJobRepository,
) -> TestClient:
    """Create a client using an isolated job repository."""

    queue = InMemoryJobQueue()
    service = JobService(
        queue=queue,
        repository=repository,
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
