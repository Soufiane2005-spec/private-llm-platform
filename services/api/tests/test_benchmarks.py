"""HTTP tests for benchmark endpoints."""

from fastapi.testclient import TestClient

from application.services.benchmark_query_service import BenchmarkQueryService
from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult
from infrastructure.persistence.in_memory_benchmark_repository import (
    InMemoryBenchmarkRepository,
)
from interfaces.http.app import create_app
from interfaces.http.routes.benchmarks import get_benchmark_service


def create_test_client(
    repository: InMemoryBenchmarkRepository,
) -> TestClient:
    """Create a client with an isolated benchmark repository."""

    service = BenchmarkQueryService(repository=repository)

    app = create_app()
    app.dependency_overrides[get_benchmark_service] = lambda: service

    return TestClient(app)


def create_record() -> BenchmarkRecord:
    """Create a benchmark record used by HTTP tests."""

    return BenchmarkRecord(
        benchmark_id="benchmark-1",
        model_id="qwen3-0.6b",
        result=BenchmarkResult(
            prompt_id="prompt-1",
            engine="vllm",
            latency_ms=500.0,
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