"""HTTP tests for benchmark endpoints."""

from fastapi.testclient import TestClient

from application.services.auth_service import AuthService
from application.services.benchmark_query_service import BenchmarkQueryService
from domain.auth.user import PlatformUser, UserRole
from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult
from domain.jobs.job import Job, JobStatus
from infrastructure.persistence.in_memory_benchmark_repository import (
    InMemoryBenchmarkRepository,
)
from infrastructure.persistence.in_memory_user_repository import InMemoryUserRepository
from infrastructure.security.jwt_token_service import JWTTokenService
from interfaces.http.app import create_app
from interfaces.http.dependencies.auth import get_auth_service
from interfaces.http.routes.benchmarks import (
    get_benchmark_execution_service,
    get_benchmark_service,
)


def create_test_client(
    repository: InMemoryBenchmarkRepository,
) -> TestClient:
    """Create a client with an isolated benchmark repository."""

    service = BenchmarkQueryService(repository=repository)

    app = create_app()
    app.dependency_overrides[get_benchmark_service] = lambda: service

    return TestClient(app)


class TestPasswordHasher:
    """Deterministic password checker."""

    def verify(self, password: str, password_hash: str) -> bool:
        return password == "correct-password" and password_hash == "hash"

    def hash(self, password: str) -> str:
        return f"hashed:{password}"


def auth_service() -> AuthService:
    """Create an auth service for protected benchmark routes."""

    return AuthService(
        user_repository=InMemoryUserRepository(
            (
                PlatformUser(
                    username="admin",
                    password_hash="hash",
                    role=UserRole.ADMIN,
                ),
            )
        ),
        password_hasher=TestPasswordHasher(),
        token_service=JWTTokenService(
            secret_key="benchmark-test-secret-long-enough-for-hs256",
            algorithm="HS256",
            expire_minutes=30,
        ),
    )


def bearer(client: TestClient) -> dict[str, str]:
    """Return auth headers."""

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "correct-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_record() -> BenchmarkRecord:
    """Create a benchmark record used by HTTP tests."""

    return BenchmarkRecord(
        benchmark_id="benchmark-1",
        model_id="qwen3-0.6b",
        result=BenchmarkResult(
            prompt_id="prompt-1",
            engine="vllm",
            latency_ms=500.0,
            ttft_ms=125.0,
            tokens_generated=100,
            duration_seconds=2.0,
        ),
        resources=BenchmarkResourceMetrics(
            cpu_percent=40.0,
            memory_percent=50.0,
            memory_used_bytes=1024,
            gpu_percent=70.0,
            gpu_memory_used_bytes=2048,
        ),
    )


class FakeBenchmarkExecutionService:
    """Fake execution service for HTTP tests."""

    def run(self, *, model, engine, prompts):
        return (
            (create_record(),),
            Job(
                job_id="job-1",
                job_type="benchmark:vllm:qwen3-0.6b",
                status=JobStatus.COMPLETED,
            ),
        )


def test_run_benchmark_returns_job_records_and_recommendation() -> None:
    """Run benchmarks through the protected HTTP endpoint."""

    app = create_app()
    app.dependency_overrides[get_benchmark_execution_service] = (
        lambda: FakeBenchmarkExecutionService()
    )
    app.dependency_overrides[get_auth_service] = auth_service
    client = TestClient(app)

    response = client.post(
        "/benchmarks",
        json={
            "model": "qwen3-0.6b",
            "engine": "vllm",
            "prompts": ["hello"],
        },
        headers=bearer(client),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["job"]["status"] == "completed"
    assert body["records"][0]["ttft_ms"] == 125.0
    assert body["recommendation"]


def test_list_benchmarks_returns_empty_list() -> None:
    repository = InMemoryBenchmarkRepository()
    client = create_test_client(repository)

    response = client.get("/benchmarks")

    assert response.status_code == 200
    assert response.json() == []


def test_list_benchmarks_returns_records() -> None:
    repository = InMemoryBenchmarkRepository()
    repository.save(create_record())

    client = create_test_client(repository)

    response = client.get("/benchmarks")

    assert response.status_code == 200

    assert response.json() == [
        {
            "benchmark_id": "benchmark-1",
            "model_id": "qwen3-0.6b",
            "prompt_id": "prompt-1",
            "engine": "vllm",
            "latency_ms": 500.0,
            "ttft_ms": 125.0,
            "tokens_generated": 100,
            "duration_seconds": 2.0,
            "throughput_tokens_per_second": 50.0,
            "resources": {
                "cpu_percent": 40.0,
                "memory_percent": 50.0,
                "memory_used_bytes": 1024,
                "gpu_percent": 70.0,
                "gpu_memory_used_bytes": 2048,
            },
        }
    ]


def test_get_benchmark_report_returns_none_when_empty() -> None:
    repository = InMemoryBenchmarkRepository()
    client = create_test_client(repository)

    response = client.get("/benchmarks/report")

    assert response.status_code == 200
    assert response.json() is None


def test_get_benchmark_report_returns_aggregated_metrics() -> None:
    repository = InMemoryBenchmarkRepository()
    repository.save(create_record())

    client = create_test_client(repository)

    response = client.get("/benchmarks/report")

    assert response.status_code == 200

    assert response.json() == {
        "benchmark_count": 1,
        "average_latency_ms": 500.0,
        "average_throughput_tokens_per_second": 50.0,
        "average_cpu_percent": 40.0,
        "average_memory_percent": 50.0,
        "average_gpu_percent": 70.0,
    }
