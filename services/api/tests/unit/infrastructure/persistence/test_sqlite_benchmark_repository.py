"""Tests for SQLite benchmark persistence."""

from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult
from infrastructure.persistence.sqlite_benchmark_repository import (
    SQLiteBenchmarkRepository,
)


def create_record(benchmark_id: str) -> BenchmarkRecord:
    """Create a benchmark record with resource metrics."""

    return BenchmarkRecord(
        benchmark_id=benchmark_id,
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


def test_sqlite_benchmark_repository_persists_records(tmp_path) -> None:
    """Benchmark records survive repository re-creation."""

    database_path = tmp_path / "platform.db"
    repository = SQLiteBenchmarkRepository(database_path)
    record = create_record("benchmark-1")

    repository.save(record)

    reloaded = SQLiteBenchmarkRepository(database_path)

    assert reloaded.list() == (record,)


def test_sqlite_benchmark_repository_replaces_records(tmp_path) -> None:
    """Benchmark records are replaceable."""

    repository = SQLiteBenchmarkRepository(tmp_path / "platform.db")
    original = create_record("benchmark-1")
    replacement = BenchmarkRecord(
        benchmark_id="benchmark-1",
        model_id="llama-3.2-1b",
        result=original.result,
        resources=original.resources,
    )

    repository.save(original)
    repository.save(replacement)

    assert repository.list() == (replacement,)
