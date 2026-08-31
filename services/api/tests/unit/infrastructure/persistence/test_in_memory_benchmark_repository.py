from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult
from infrastructure.persistence.in_memory_benchmark_repository import (
    InMemoryBenchmarkRepository,
)


def create_record(
    benchmark_id: str,
) -> BenchmarkRecord:
    return BenchmarkRecord(
        benchmark_id=benchmark_id,
        model_id="model-1",
        result=BenchmarkResult(
            prompt_id="prompt-1",
            engine="ollama",
            latency_ms=100.0,
        ),
        resources=BenchmarkResourceMetrics(
            cpu_percent=10.0,
            memory_percent=20.0,
            memory_used_bytes=1000,
        ),
    )


def test_save_and_list_records() -> None:
    repository = InMemoryBenchmarkRepository()

    second = create_record("benchmark-b")
    first = create_record("benchmark-a")

    repository.save(second)
    repository.save(first)

    assert repository.list() == (
        first,
        second,
    )


def test_save_replaces_existing_record() -> None:
    repository = InMemoryBenchmarkRepository()

    original = create_record("benchmark-1")
    replacement = BenchmarkRecord(
        benchmark_id="benchmark-1",
        model_id="model-2",
        result=original.result,
        resources=original.resources,
    )

    repository.save(original)
    repository.save(replacement)

    assert repository.list() == (replacement,)