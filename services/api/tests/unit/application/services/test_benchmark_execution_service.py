"""Tests for dynamic benchmark execution model resolution."""

import pytest

from application.ports.benchmark_executor import BenchmarkExecution
from application.services.benchmark_execution_service import BenchmarkExecutionService
from application.services.job_service import JobService
from application.services.model_catalog import ModelCatalog
from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry
from infrastructure.persistence.in_memory_benchmark_repository import (
    InMemoryBenchmarkRepository,
)
from infrastructure.persistence.in_memory_job_repository import InMemoryJobRepository
from infrastructure.persistence.in_memory_model_catalog_repository import (
    InMemoryModelCatalogRepository,
)
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue


class FakeExecutor:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.models: list[str] = []
        self.error = error

    def execute(self, *, model: str, prompt: str) -> BenchmarkExecution:
        self.models.append(model)
        if self.error is not None:
            raise self.error
        return BenchmarkExecution(
            total_latency_ms=100,
            ttft_ms=50,
            tokens_generated=10,
            duration_seconds=1,
        )


class FakeResourceSampler:
    def get_system_usage(self):
        return type(
            "Usage",
            (),
            {
                "cpu_percent": 10.0,
                "memory_percent": 20.0,
                "memory_used_bytes": 1024,
                "gpu_percent": 30.0,
                "gpu_memory_used_bytes": 2048,
            },
        )()


class FakeRuntimeAvailability:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.checked: list[str] = []

    def require_benchmark_eligible(self, model: ModelCatalogEntry) -> None:
        self.checked.append(model.model_id)
        if not self.available:
            raise ValueError(f"Model '{model.model_id}' is not benchmark eligible.")


class TimeoutExecutor:
    def execute(self, *, model: str, prompt: str) -> BenchmarkExecution:
        import time

        time.sleep(0.2)
        return BenchmarkExecution(
            total_latency_ms=100,
            ttft_ms=50,
            tokens_generated=10,
            duration_seconds=1,
        )


class FailingBenchmarkRepository(InMemoryBenchmarkRepository):
    def save(self, record: BenchmarkRecord) -> None:
        raise RuntimeError("benchmark persistence failed")


def catalog() -> ModelCatalog:
    repository = InMemoryModelCatalogRepository()
    repository.save(
        ModelCatalogEntry(
            model_id="phi3-mini",
            display_name="Phi-3 Mini",
            engine=LLMEngine.OLLAMA,
            engine_model_id="phi3:mini",
        )
    )
    repository.save(
        ModelCatalogEntry(
            model_id="smollm2-135m",
            display_name="SmolLM2 135M",
            engine=LLMEngine.VLLM,
            engine_model_id="HuggingFaceTB/SmolLM2-135M-Instruct",
            served_model_name="smollm2-135m",
            gpu_required=True,
        )
    )
    return ModelCatalog(repository=repository)


def service(
    *,
    ollama_executor: FakeExecutor | None = None,
    vllm_executor: FakeExecutor | None = None,
    runtime: FakeRuntimeAvailability | None = None,
    repository: InMemoryBenchmarkRepository | None = None,
    job_repository: InMemoryJobRepository | None = None,
    timeout_seconds: float = 120.0,
) -> BenchmarkExecutionService:
    job_repository = job_repository or InMemoryJobRepository()
    return BenchmarkExecutionService(
        repository=repository or InMemoryBenchmarkRepository(),
        jobs=JobService(queue=InMemoryJobQueue(), repository=job_repository),
        job_repository=job_repository,
        model_catalog=catalog(),
        ollama_executor=ollama_executor or FakeExecutor(),
        vllm_executor=vllm_executor or FakeExecutor(),
        resource_sampler=FakeResourceSampler(),
        runtime_availability=runtime or FakeRuntimeAvailability(),
        timeout_seconds=timeout_seconds,
    )


def test_ollama_benchmark_resolves_catalog_model_to_engine_model_id() -> None:
    executor = FakeExecutor()
    records, job = service(ollama_executor=executor).run(
        model="phi3-mini",
        engine=LLMEngine.OLLAMA,
        prompts=("hello",),
    )

    assert job.status.value == "completed"
    assert executor.models == ["phi3:mini"]
    assert records[0].model_id == "phi3-mini"


def test_vllm_benchmark_resolves_catalog_model_to_served_model_name() -> None:
    executor = FakeExecutor()
    records, job = service(vllm_executor=executor).run(
        model="smollm2-135m",
        engine=LLMEngine.VLLM,
        prompts=("hello",),
    )

    assert job.status.value == "completed"
    assert executor.models == ["smollm2-135m"]
    assert records[0].model_id == "smollm2-135m"


def test_benchmark_start_rejects_unavailable_runtime_before_creating_job() -> None:
    runtime = FakeRuntimeAvailability(available=False)

    with pytest.raises(ValueError, match="not benchmark eligible"):
        service(runtime=runtime).start(
            model="phi3-mini",
            engine=LLMEngine.OLLAMA,
            prompts=("hello",),
        )

    assert runtime.checked == ["phi3-mini"]


def test_execute_job_success_marks_job_completed() -> None:
    job_repository = InMemoryJobRepository()
    benchmark_service = service(job_repository=job_repository)
    job = benchmark_service.start(
        model="phi3-mini",
        engine=LLMEngine.OLLAMA,
        prompts=("hello",),
    )

    records = benchmark_service.execute_job(
        job_id=job.job_id,
        model="phi3-mini",
        engine=LLMEngine.OLLAMA,
        prompts=("hello",),
    )

    assert len(records) == 1
    assert job_repository.get(job.job_id).status.value == "completed"
    assert job_repository.get(job.job_id).status.value == "completed"


def test_execute_job_executor_error_marks_job_failed() -> None:
    job_repository = InMemoryJobRepository()
    benchmark_service = service(
        ollama_executor=FakeExecutor(error=RuntimeError("runtime exploded")),
        job_repository=job_repository,
    )
    job = benchmark_service.start(
        model="phi3-mini",
        engine=LLMEngine.OLLAMA,
        prompts=("hello",),
    )

    records = benchmark_service.execute_job(
        job_id=job.job_id,
        model="phi3-mini",
        engine=LLMEngine.OLLAMA,
        prompts=("hello",),
    )

    final_job = job_repository.get(job.job_id)
    assert records == ()
    assert final_job.status.value == "failed"
    assert final_job.error == "runtime exploded"


def test_execute_job_timeout_marks_job_failed() -> None:
    job_repository = InMemoryJobRepository()
    benchmark_service = service(
        ollama_executor=TimeoutExecutor(),
        job_repository=job_repository,
        timeout_seconds=0.01,
    )
    job = benchmark_service.start(
        model="phi3-mini",
        engine=LLMEngine.OLLAMA,
        prompts=("hello",),
    )

    records = benchmark_service.execute_job(
        job_id=job.job_id,
        model="phi3-mini",
        engine=LLMEngine.OLLAMA,
        prompts=("hello",),
    )

    final_job = job_repository.get(job.job_id)
    assert records == ()
    assert final_job.status.value == "failed"
    assert "timed out" in final_job.error


def test_execute_job_persistence_error_marks_job_failed() -> None:
    job_repository = InMemoryJobRepository()
    benchmark_service = service(
        repository=FailingBenchmarkRepository(),
        job_repository=job_repository,
    )
    job = benchmark_service.start(
        model="phi3-mini",
        engine=LLMEngine.OLLAMA,
        prompts=("hello",),
    )

    records = benchmark_service.execute_job(
        job_id=job.job_id,
        model="phi3-mini",
        engine=LLMEngine.OLLAMA,
        prompts=("hello",),
    )

    final_job = job_repository.get(job.job_id)
    assert records == ()
    assert final_job.status.value == "failed"
    assert final_job.error == "benchmark persistence failed"
