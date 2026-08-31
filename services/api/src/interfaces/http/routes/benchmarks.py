"""HTTP routes for benchmark visualization."""

from typing import Annotated

from fastapi import APIRouter, Depends

from application.services.benchmark_query_service import BenchmarkQueryService
from infrastructure.persistence.in_memory_benchmark_repository import (
    InMemoryBenchmarkRepository,
)
from interfaces.http.schemas.benchmarks import (
    BenchmarkReportResponse,
    BenchmarkResourceResponse,
    BenchmarkResponse,
)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

_repository = InMemoryBenchmarkRepository()
_service = BenchmarkQueryService(repository=_repository)


def get_benchmark_service() -> BenchmarkQueryService:
    """Return the benchmark query service."""

    return _service


BenchmarkServiceDependency = Annotated[
    BenchmarkQueryService,
    Depends(get_benchmark_service),
]


@router.get("", response_model=list[BenchmarkResponse])
def list_benchmarks(
    service: BenchmarkServiceDependency,
) -> list[BenchmarkResponse]:
    """Return all benchmark results."""

    return [
        BenchmarkResponse(
            benchmark_id=record.benchmark_id,
            model_id=record.model_id,
            prompt_id=record.prompt_id,
            engine=record.engine,
            latency_ms=record.result.latency_ms,
            tokens_generated=record.result.tokens_generated,
            duration_seconds=record.result.duration_seconds,
            throughput_tokens_per_second=(
                record.throughput_tokens_per_second
            ),
            resources=BenchmarkResourceResponse(
                cpu_percent=record.resources.cpu_percent,
                memory_percent=record.resources.memory_percent,
                memory_used_bytes=record.resources.memory_used_bytes,
                gpu_percent=record.resources.gpu_percent,
                gpu_memory_used_bytes=(
                    record.resources.gpu_memory_used_bytes
                ),
            ),
        )
        for record in service.list_records()
    ]


@router.get(
    "/report",
    response_model=BenchmarkReportResponse | None,
)
def get_benchmark_report(
    service: BenchmarkServiceDependency,
) -> BenchmarkReportResponse | None:
    """Return the aggregated benchmark report."""

    report = service.generate_report()

    if report is None:
        return None

    return BenchmarkReportResponse(
        benchmark_count=report.benchmark_count,
        average_latency_ms=report.average_latency_ms,
        average_throughput_tokens_per_second=(
            report.average_throughput_tokens_per_second
        ),
        average_cpu_percent=report.average_cpu_percent,
        average_memory_percent=report.average_memory_percent,
        average_gpu_percent=report.average_gpu_percent,
    )