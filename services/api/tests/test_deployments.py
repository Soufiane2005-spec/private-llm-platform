"""HTTP tests for model deployment lifecycle endpoints."""

from fastapi.testclient import TestClient

from application.services.auth_service import AuthService
from application.services.job_service import JobService
from application.services.model_deployment_service import ModelDeploymentService
from domain.auth.user import PlatformUser, UserRole
from domain.models.deployment import ModelDeployment
from domain.models.llm_engine import LLMEngine
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


class FakeOllamaRuntimeClient:
    """In-memory double for the Ollama runtime model management port."""

    def __init__(
        self,
        *,
        initial_models: tuple[str, ...] = (),
        fail_pull_with: Exception | None = None,
    ) -> None:
        self._models = set(initial_models)
        self._fail_pull_with = fail_pull_with
        self.pull_calls: list[str] = []

    def has_model(self, model: str) -> bool:
        return model in self._models

    def pull_model(self, model: str) -> None:
        self.pull_calls.append(model)
        if self._fail_pull_with is not None:
            raise self._fail_pull_with
        self._models.add(model)

    def ensure_model_available(self, model: str) -> bool:
        if self.has_model(model):
            return False
        self.pull_model(model)
        return True


class FailingDeploymentManager:
    """Deployment manager that raises to exercise persisted failure state."""

    def deploy(self, deployment: ModelDeployment) -> ModelDeployment:
        raise RuntimeError("runtime exploded")

    def start(self, deployment: ModelDeployment) -> ModelDeployment:
        raise RuntimeError("runtime exploded")

    def stop(self, deployment: ModelDeployment) -> ModelDeployment:
        raise RuntimeError("runtime exploded")

    def restart(self, deployment: ModelDeployment) -> ModelDeployment:
        raise RuntimeError("runtime exploded")

    def delete(self, deployment: ModelDeployment) -> None:
        raise RuntimeError("runtime exploded")

    def status(self, deployment: ModelDeployment) -> ModelDeployment:
        return deployment


def create_client(
    role: UserRole = UserRole.ADMIN,
    *,
    ollama_client: FakeOllamaRuntimeClient | None = None,
) -> TestClient:
    """Create a test client with isolated deployment state."""

    job_repository = InMemoryJobRepository()
    job_service = JobService(
        queue=InMemoryJobQueue(),
        repository=job_repository,
    )
    deployment_service = ModelDeploymentService(
        deployments=InMemoryModelDeploymentRepository(),
        manager=LocalModelDeploymentManager(
            gpu_available=False,
            ollama_client=(
                ollama_client
                if ollama_client is not None
                else FakeOllamaRuntimeClient(
                    initial_models=("qwen2.5:1.5b", "llama3.2:1b")
                )
            ),
        ),
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
    assert final_deployment.json()["runtime_state"] == "ollama-model-already-present"
    assert final_job.status_code == 200
    assert final_job.json()["status"] == "completed"


def test_deploy_ollama_model_pulls_when_absent() -> None:
    """Deploying a catalog model absent from Ollama triggers a real pull."""

    fake_client = FakeOllamaRuntimeClient(initial_models=())
    client = create_client(ollama_client=fake_client)

    response = client.post(
        "/deployments",
        json={"model": "phi3:mini", "engine": "ollama"},
        headers=auth_headers(client),
    )

    assert response.status_code == 202
    deployment_id = response.json()["deployment"]["deployment_id"]

    final_deployment = client.get(
        f"/deployments/{deployment_id}",
        headers=auth_headers(client),
    ).json()

    assert fake_client.pull_calls == ["phi3:mini"]
    assert fake_client.has_model("phi3:mini") is True
    assert final_deployment["status"] == "running"
    assert final_deployment["runtime_state"] == "ollama-model-pulled"


def test_deploy_ollama_model_already_present_is_idempotent() -> None:
    """Deploying a model already present in Ollama does not re-pull it."""

    fake_client = FakeOllamaRuntimeClient(initial_models=("phi3:mini",))
    client = create_client(ollama_client=fake_client)

    response = client.post(
        "/deployments",
        json={"model": "phi3:mini", "engine": "ollama"},
        headers=auth_headers(client),
    )
    deployment_id = response.json()["deployment"]["deployment_id"]

    final_deployment = client.get(
        f"/deployments/{deployment_id}",
        headers=auth_headers(client),
    ).json()

    assert fake_client.pull_calls == []
    assert final_deployment["status"] == "running"
    assert final_deployment["runtime_state"] == "ollama-model-already-present"


def test_deploy_ollama_model_pull_failure_reports_clear_error() -> None:
    """A failed Ollama pull surfaces a useful error and does not fake success."""

    fake_client = FakeOllamaRuntimeClient(
        initial_models=(),
        fail_pull_with=RuntimeError("no space left on device"),
    )
    client = create_client(ollama_client=fake_client)

    response = client.post(
        "/deployments",
        json={"model": "phi3:mini", "engine": "ollama"},
        headers=auth_headers(client),
    )
    deployment_id = response.json()["deployment"]["deployment_id"]
    job_id = response.json()["job"]["job_id"]

    final_deployment = client.get(
        f"/deployments/{deployment_id}",
        headers=auth_headers(client),
    ).json()
    final_job = client.get(f"/jobs/{job_id}").json()

    assert final_deployment["status"] == "failed"
    assert final_deployment["runtime_state"] == "ollama-pull-failed"
    assert "phi3:mini" in final_deployment["error"]
    assert "no space left on device" in final_deployment["error"]
    assert final_job["status"] == "failed"


def test_deploy_operation_exception_marks_deployment_failed() -> None:
    """Manager exceptions do not leave deployment records stuck as deploying."""

    job_repository = InMemoryJobRepository()
    job_service = JobService(
        queue=InMemoryJobQueue(),
        repository=job_repository,
    )
    deployment_repository = InMemoryModelDeploymentRepository()
    deployment_service = ModelDeploymentService(
        deployments=deployment_repository,
        manager=FailingDeploymentManager(),
        jobs=job_service,
        job_repository=job_repository,
        timeout_seconds=5,
    )

    deployment, job = deployment_service.deploy(
        model="phi3-mini",
        engine=LLMEngine.OLLAMA,
    )

    final_job = deployment_service.execute_deploy(
        deployment.deployment_id,
        job.job_id,
    )
    final_deployment = deployment_service.get_deployment(deployment.deployment_id)

    assert final_job.status.value == "failed"
    assert final_deployment.status.value == "failed"
    assert final_deployment.runtime_state == "operation-failed"
    assert final_deployment.error == "runtime exploded"


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

    blocked_delete_response = client.delete(
        f"/deployments/{deployment_id}",
        headers=headers,
    )
    assert blocked_delete_response.status_code == 409

    client.post(
        f"/deployments/{deployment_id}/stop",
        headers=headers,
    )

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
