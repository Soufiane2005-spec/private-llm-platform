"""Tests for benchmark report generation."""

import pytest

from application.services.benchmark_report_service import (
    BenchmarkReportService,
)
from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult


def create_record(
    benchmark_id: str,
    latency_ms: float,
    tokens_generated: int,
    duration_seconds: float,
    cpu_percent: float,
    memory_percent: float,
    gpu_percent: float | None,
) -> BenchmarkRecord:
    """Create a benchmark record for tests."""

    return BenchmarkRecord(
        benchmark_id=benchmark_id,
        model_id="qwen3-0.6b",
        result=BenchmarkResult(
            prompt_id=f"prompt-{benchmark_id}",
            engine="vllm",
            latency_ms=latency_ms,
            tokens_generated=tokens_generated,
            duration_seconds=duration_seconds,
        ),
        resources=BenchmarkResourceMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_bytes=4_000_000_000,
            gpu_percent=gpu_percent,
            gpu_memory_used_bytes=(
                2_000_000_000
                if gpu_percent is not None
                else None
            ),
        ),
    )


def test_report_service_generates_averages() -> None:
    service = BenchmarkReportService()

    records = [
        create_record(
            benchmark_id="1",
            latency_ms=100.0,
            tokens_generated=100,
            duration_seconds=2.0,
            cpu_percent=40.0,
            memory_percent=50.0,
            gpu_percent=60.0,
        ),
        create_record(
            benchmark_id="2",
            latency_ms=200.0,
            tokens_generated=200,
            duration_seconds=4.0,
            cpu_percent=60.0,
            memory_percent=70.0,
            gpu_percent=80.0,
        ),
    ]

    report = service.generate(records)

    assert report.benchmark_count == 2
    assert report.average_latency_ms == 150.0
    assert report.average_throughput_tokens_per_second == 50.0
    assert report.average_cpu_percent == 50.0
    assert report.average_memory_percent == 60.0
    assert report.average_gpu_percent == 70.0


def test_report_service_supports_cpu_only_records() -> None:
    service = BenchmarkReportService()

    record = create_record(
        benchmark_id="1",
        latency_ms=100.0,
        tokens_generated=100,
        duration_seconds=2.0,
        cpu_percent=40.0,
        memory_percent=50.0,
        gpu_percent=None,
    )

    report = service.generate([record])

    assert report.average_gpu_percent is None


def test_report_service_averages_only_available_gpu_values() -> None:
    service = BenchmarkReportService()

    records = [
        create_record(
            benchmark_id="1",
            latency_ms=100.0,
            tokens_generated=100,
            duration_seconds=2.0,
            cpu_percent=40.0,
            memory_percent=50.0,
            gpu_percent=80.0,
        ),
        create_record(
            benchmark_id="2",
            latency_ms=100.0,
            tokens_generated=100,
            duration_seconds=2.0,
            cpu_percent=40.0,
            memory_percent=50.0,
            gpu_percent=None,
        ),
    ]

    report = service.generate(records)

    assert report.average_gpu_percent == 80.0


def test_report_service_rejects_empty_records() -> None:
    service = BenchmarkReportService()

    with pytest.raises(
        ValueError,
        match="at least one benchmark record is required",
    ):
        service.generate([])