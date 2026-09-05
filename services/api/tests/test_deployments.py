"""HTTP tests for model deployment lifecycle endpoints."""

from fastapi.testclient import TestClient

from application.services.auth_service import AuthService
from application.services.job_service import JobService
from application.services.model_deployment_service import ModelDeploymentService
from domain.auth.user import PlatformUser, UserRole
from infrastructure.models.local_model_deployment_manager import (
    LocalModelDeploymentManager,
)
from infrastructure.persistence.in_memory_job_repository import InMemoryJobRepository
from infrastructure.persistence.in_memory_model_deployment_repository import (
    InMemoryModelDeploymentRepository,
)
from infrastructure.persistence.in_memory_user_repository import InMemoryUserRepository
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue
from infrastructure.security.jwt_token_service import JWTTokenService
from interfaces.http.app import create_app
from interfaces.http.dependencies.auth import get_auth_service
from interfaces.http.routes.deployments import get_deployment_service
from interfaces.http.routes.jobs import get_job_service

SECRET_KEY = "deployment-test-secret-long-enough-for-hs256"
PASSWORD = "correct-password"
PASSWORD_HASH = "deployment-test-hash"


class TestPasswordHasher:
    """Deterministic password verifier used by HTTP tests."""

    def verify(self, password: str, password_hash: str) -> bool:
        return password == PASSWORD and password_hash == PASSWORD_HASH


def create_client(role: UserRole = UserRole.ADMIN) -> TestClient:
    """Create a test client with isolated deployment state."""

    job_repository = InMemoryJobRepository()
    job_service = JobService(
        queue=InMemoryJobQueue(),
        repository=job_repository,
    )
    deployment_service = ModelDeploymentService(
        deployments=InMemoryModelDeploymentRepository(),
        manager=LocalModelDeploymentManager(gpu_available=False),
        jobs=job_service,
        job_repository=job_repository,
    )
    auth_service = AuthService(
        user_repository=InMemoryUserRepository(
            (
                PlatformUser(
                    username="admin",
                    password_hash=PASSWORD_HASH,
                    role=role,
                ),
            )
        ),
        password_hasher=TestPasswordHasher(),
        token_service=JWTTokenService(
            secret_key=SECRET_KEY,
            algorithm="HS256",
            expire_minutes=30,
        ),
    )

    app = create_app()
    app.dependency_overrides[get_deployment_service] = lambda: deployment_service
    app.dependency_overrides[get_job_service] = lambda: job_service
    app.dependency_overrides[get_auth_service] = lambda: auth_service

    return TestClient(app)


def auth_headers(client: TestClient) -> dict[str, str]:
    """Return bearer auth headers for the test admin."""

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": PASSWORD},
    )

    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_deploy_ollama_model_creates_async_job() -> None:
    """Deploying an Ollama model returns immediately and completes in background."""

    client = create_client()

    response = client.post(
        "/deployments",
        json={"model": "qwen2.5:1.5b", "engine": "ollama"},
        headers=auth_headers(client),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["deployment"]["model"] == "qwen2.5:1.5b"
    assert body["deployment"]["engine"] == "ollama"
    assert body["deployment"]["status"] == "deploying"
    assert body["deployment"]["runtime_state"] == "deployment-job-submitted"
    assert body["job"]["status"] == "pending"

    deployment_id = body["deployment"]["deployment_id"]
    job_id = body["job"]["job_id"]

    final_deployment = client.get(
        f"/deployments/{deployment_id}",
        headers=auth_headers(client),
    )
    final_job = client.get(f"/jobs/{job_id}")

    assert final_deployment.status_code == 200
    assert final_deployment.json()["status"] == "running"
    assert final_deployment.json()["runtime_state"] == "local-runtime-ready"
    assert final_job.status_code == 200
    assert final_job.json()["status"] == "completed"


def test_deploy_vllm_without_gpu_fails_with_clear_reason() -> None:
    """vLLM does not pretend to run when no GPU is available."""

    client = create_client()

    response = client.post(
        "/deployments",
        json={"model": "Qwen/Qwen3-0.6B", "engine": "vllm"},
        headers=auth_headers(client),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["deployment"]["status"] == "deploying"
    assert body["job"]["status"] == "pending"

    deployment_id = body["deployment"]["deployment_id"]
    job_id = body["job"]["job_id"]

    final_deployment = client.get(
        f"/deployments/{deployment_id}",
        headers=auth_headers(client),
    ).json()
    final_job = client.get(f"/jobs/{job_id}").json()

    assert final_deployment["status"] == "failed"
    assert final_deployment["runtime_state"] == "gpu-unavailable"
    assert final_deployment["gpu_available"] is False
    assert "requires an NVIDIA GPU" in final_deployment["error"]
    assert final_job["status"] == "failed"


def test_viewer_can_list_but_cannot_deploy() -> None:
    """Viewer role is read-only for model deployment operations."""

    client = create_client(UserRole.VIEWER)
    headers = auth_headers(client)

    list_response = client.get("/deployments", headers=headers)
    deploy_response = client.post(
        "/deployments",
        json={"model": "llama3.2:1b", "engine": "ollama"},
        headers=headers,
    )

    assert list_response.status_code == 200
    assert deploy_response.status_code == 403


def test_start_stop_restart_and_delete_deployment() -> None:
    """Lifecycle actions update deployment state and create jobs."""

    client = create_client()
    headers = auth_headers(client)

    created = client.post(
        "/deployments",
        json={"model": "llama3.2:1b", "engine": "ollama"},
        headers=headers,
    ).json()
    deployment_id = created["deployment"]["deployment_id"]

    stop_response = client.post(
        f"/deployments/{deployment_id}/stop",
        headers=headers,
    )

    assert stop_response.status_code == 200
    assert stop_response.json()["job"]["status"] == "pending"
    assert client.get(
        f"/deployments/{deployment_id}",
        headers=headers,
    ).json()["status"] == "stopped"

    start_response = client.post(
        f"/deployments/{deployment_id}/start",
        headers=headers,
    )

    assert start_response.status_code == 200
    assert start_response.json()["job"]["status"] == "pending"
    assert client.get(
        f"/deployments/{deployment_id}",
        headers=headers,
    ).json()["status"] == "running"

    restart_response = client.post(
        f"/deployments/{deployment_id}/restart",
        headers=headers,
    )

    assert restart_response.status_code == 200
    assert restart_response.json()["job"]["status"] == "pending"
    assert client.get(
        f"/deployments/{deployment_id}",
        headers=headers,
    ).json()["status"] == "running"

    delete_response = client.delete(
        f"/deployments/{deployment_id}",
        headers=headers,
    )
    get_deleted_response = client.get(
        f"/deployments/{deployment_id}",
        headers=headers,
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["deployment"] is None
    assert delete_response.json()["job"]["status"] == "pending"
    assert get_deleted_response.status_code == 404
