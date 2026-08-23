"""Tests for aggregated benchmark records."""

import pytest

from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult


def create_result() -> BenchmarkResult:
    return BenchmarkResult(
        prompt_id="prompt-1",
        engine="vllm",
        latency_ms=100.0,
        tokens_generated=200,
        duration_seconds=4.0,
    )


def create_resources() -> BenchmarkResourceMetrics:
    return BenchmarkResourceMetrics(
        cpu_percent=40.0,
        memory_percent=60.0,
        memory_used_bytes=4_000_000_000,
        gpu_percent=70.0,
        gpu_memory_used_bytes=2_000_000_000,
    )


def test_benchmark_record_can_be_created() -> None:
    record = BenchmarkRecord(
        benchmark_id="benchmark-1",
        model_id="qwen3-0.6b",
        result=create_result(),
        resources=create_resources(),
    )

    assert record.benchmark_id == "benchmark-1"
    assert record.model_id == "qwen3-0.6b"
    assert record.engine == "vllm"
    assert record.prompt_id == "prompt-1"
    assert record.latency_ms == 100.0
    assert record.throughput_tokens_per_second == 50.0


def test_benchmark_record_exposes_resource_metrics() -> None:
    resources = create_resources()

    record = BenchmarkRecord(
        benchmark_id="benchmark-1",
        model_id="qwen3-0.6b",
        result=create_result(),
        resources=resources,
    )

    assert record.resources == resources
    assert record.resources.cpu_percent == 40.0
    assert record.resources.memory_percent == 60.0
    assert record.resources.gpu_percent == 70.0


@pytest.mark.parametrize(
    "benchmark_id",
    [
        "",
        " ",
        "   ",
    ],
)
def test_benchmark_record_rejects_empty_benchmark_id(
    benchmark_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="benchmark_id cannot be empty",
    ):
        BenchmarkRecord(
            benchmark_id=benchmark_id,
            model_id="qwen3-0.6b",
            result=create_result(),
            resources=create_resources(),
        )


@pytest.mark.parametrize(
    "model_id",
    [
        "",
        " ",
        "   ",
    ],
)
def test_benchmark_record_rejects_empty_model_id(
    model_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="model_id cannot be empty",
    ):
        BenchmarkRecord(
            benchmark_id="benchmark-1",
            model_id=model_id,
            result=create_result(),
            resources=create_resources(),
        )