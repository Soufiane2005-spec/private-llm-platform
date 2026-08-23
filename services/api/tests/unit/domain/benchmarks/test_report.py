"""Tests for benchmark report domain model."""

import pytest

from domain.benchmarks.report import BenchmarkReport


def test_benchmark_report_can_be_created() -> None:
    report = BenchmarkReport(
        benchmark_count=3,
        average_latency_ms=120.0,
        average_throughput_tokens_per_second=45.0,
        average_cpu_percent=50.0,
        average_memory_percent=60.0,
        average_gpu_percent=70.0,
    )

    assert report.benchmark_count == 3
    assert report.average_latency_ms == 120.0
    assert report.average_throughput_tokens_per_second == 45.0
    assert report.average_cpu_percent == 50.0
    assert report.average_memory_percent == 60.0
    assert report.average_gpu_percent == 70.0


def test_benchmark_report_supports_no_gpu() -> None:
    report = BenchmarkReport(
        benchmark_count=1,
        average_latency_ms=100.0,
        average_throughput_tokens_per_second=20.0,
        average_cpu_percent=30.0,
        average_memory_percent=40.0,
    )

    assert report.average_gpu_percent is None


def test_benchmark_report_rejects_empty_report() -> None:
    with pytest.raises(
        ValueError,
        match="benchmark_count must be greater than zero",
    ):
        BenchmarkReport(
            benchmark_count=0,
            average_latency_ms=100.0,
            average_throughput_tokens_per_second=20.0,
            average_cpu_percent=30.0,
            average_memory_percent=40.0,
        )


def test_benchmark_report_rejects_negative_latency() -> None:
    with pytest.raises(
        ValueError,
        match="average_latency_ms cannot be negative",
    ):
        BenchmarkReport(
            benchmark_count=1,
            average_latency_ms=-1.0,
            average_throughput_tokens_per_second=20.0,
            average_cpu_percent=30.0,
            average_memory_percent=40.0,
        )


def test_benchmark_report_rejects_negative_throughput() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "average_throughput_tokens_per_second "
            "cannot be negative"
        ),
    ):
        BenchmarkReport(
            benchmark_count=1,
            average_latency_ms=100.0,
            average_throughput_tokens_per_second=-1.0,
            average_cpu_percent=30.0,
            average_memory_percent=40.0,
        )


@pytest.mark.parametrize(
    "cpu_percent",
    [-1.0, 100.1],
)
def test_benchmark_report_rejects_invalid_cpu(
    cpu_percent: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="average_cpu_percent must be between 0 and 100",
    ):
        BenchmarkReport(
            benchmark_count=1,
            average_latency_ms=100.0,
            average_throughput_tokens_per_second=20.0,
            average_cpu_percent=cpu_percent,
            average_memory_percent=40.0,
        )


@pytest.mark.parametrize(
    "memory_percent",
    [-1.0, 100.1],
)
def test_benchmark_report_rejects_invalid_memory(
    memory_percent: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="average_memory_percent must be between 0 and 100",
    ):
        BenchmarkReport(
            benchmark_count=1,
            average_latency_ms=100.0,
            average_throughput_tokens_per_second=20.0,
            average_cpu_percent=30.0,
            average_memory_percent=memory_percent,
        )


@pytest.mark.parametrize(
    "gpu_percent",
    [-1.0, 100.1],
)
def test_benchmark_report_rejects_invalid_gpu(
    gpu_percent: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="average_gpu_percent must be between 0 and 100",
    ):
        BenchmarkReport(
            benchmark_count=1,
            average_latency_ms=100.0,
            average_throughput_tokens_per_second=20.0,
            average_cpu_percent=30.0,
            average_memory_percent=40.0,
            average_gpu_percent=gpu_percent,
        )