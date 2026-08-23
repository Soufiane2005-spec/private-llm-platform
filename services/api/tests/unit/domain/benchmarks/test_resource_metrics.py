"""Tests for benchmark resource metrics."""

import pytest

from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics


def test_resource_metrics_can_be_created() -> None:
    metrics = BenchmarkResourceMetrics(
        cpu_percent=42.5,
        memory_percent=61.0,
        memory_used_bytes=4_000_000_000,
        gpu_percent=75.0,
        gpu_memory_used_bytes=2_000_000_000,
    )

    assert metrics.cpu_percent == 42.5
    assert metrics.memory_percent == 61.0
    assert metrics.memory_used_bytes == 4_000_000_000
    assert metrics.gpu_percent == 75.0
    assert metrics.gpu_memory_used_bytes == 2_000_000_000


def test_resource_metrics_support_no_gpu() -> None:
    metrics = BenchmarkResourceMetrics(
        cpu_percent=20.0,
        memory_percent=40.0,
        memory_used_bytes=1_000_000_000,
    )

    assert metrics.gpu_percent is None
    assert metrics.gpu_memory_used_bytes is None


@pytest.mark.parametrize(
    "cpu_percent",
    [-1.0, 100.1],
)
def test_resource_metrics_reject_invalid_cpu(
    cpu_percent: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="cpu_percent must be between 0 and 100",
    ):
        BenchmarkResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=50.0,
            memory_used_bytes=1,
        )


@pytest.mark.parametrize(
    "memory_percent",
    [-1.0, 100.1],
)
def test_resource_metrics_reject_invalid_memory(
    memory_percent: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="memory_percent must be between 0 and 100",
    ):
        BenchmarkResourceMetrics(
            cpu_percent=50.0,
            memory_percent=memory_percent,
            memory_used_bytes=1,
        )


def test_resource_metrics_reject_negative_memory_bytes() -> None:
    with pytest.raises(
        ValueError,
        match="memory_used_bytes cannot be negative",
    ):
        BenchmarkResourceMetrics(
            cpu_percent=50.0,
            memory_percent=50.0,
            memory_used_bytes=-1,
        )


@pytest.mark.parametrize(
    "gpu_percent",
    [-1.0, 100.1],
)
def test_resource_metrics_reject_invalid_gpu(
    gpu_percent: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="gpu_percent must be between 0 and 100",
    ):
        BenchmarkResourceMetrics(
            cpu_percent=50.0,
            memory_percent=50.0,
            memory_used_bytes=1,
            gpu_percent=gpu_percent,
        )


def test_resource_metrics_reject_negative_gpu_memory_bytes() -> None:
    with pytest.raises(
        ValueError,
        match="gpu_memory_used_bytes cannot be negative",
    ):
        BenchmarkResourceMetrics(
            cpu_percent=50.0,
            memory_percent=50.0,
            memory_used_bytes=1,
            gpu_percent=50.0,
            gpu_memory_used_bytes=-1,
        )