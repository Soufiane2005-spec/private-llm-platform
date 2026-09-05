"""HTTP routes for benchmark visualization."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from application.services.benchmark_execution_service import BenchmarkExecutionService
from application.services.benchmark_query_service import BenchmarkQueryService
from application.services.job_service import JobService
from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.jobs.job import Job
from infrastructure.config import get_settings
from infrastructure.llm.ollama_benchmark_executor import OllamaBenchmarkExecutor
from infrastructure.monitoring.resource_provider import SystemResourceProvider
from infrastructure.persistence.factory import (
    get_persistent_benchmark_repository,
    get_persistent_job_repository,
)
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue
from interfaces.http.dependencies.auth import EngineerUserDependency
from interfaces.http.schemas.benchmarks import (
    BenchmarkJobResponse,
    BenchmarkReportResponse,
    BenchmarkResourceResponse,
    BenchmarkResponse,
    BenchmarkRunRequest,
    BenchmarkRunResponse,
)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

_repository = get_persistent_benchmark_repository()
_service = BenchmarkQueryService(repository=_repository)
_job_repository = get_persistent_job_repository()
_job_service = JobService(
    queue=InMemoryJobQueue(),
    repository=_job_repository,
)
_execution_service = BenchmarkExecutionService(
    repository=_repository,
    jobs=_job_service,
    job_repository=_job_repository,
    ollama_executor=OllamaBenchmarkExecutor(
        base_url=get_settings().ollama_base_url,
        timeout_seconds=get_settings().ollama_timeout_seconds,
    ),
    resource_sampler=SystemResourceProvider(),
)


def get_benchmark_service() -> BenchmarkQueryService:
    """Return the benchmark query service."""

    return _service


def get_benchmark_execution_service() -> BenchmarkExecutionService:
    """Return the benchmark execution service."""

    return _execution_service


BenchmarkServiceDependency = Annotated[
    BenchmarkQueryService,
    Depends(get_benchmark_service),
]

BenchmarkExecutionServiceDependency = Annotated[
    BenchmarkExecutionService,
    Depends(get_benchmark_execution_service),
]


def _record_response(record: BenchmarkRecord) -> BenchmarkResponse:
    return BenchmarkResponse(
        benchmark_id=record.benchmark_id,
        model_id=record.model_id,
        prompt_id=record.prompt_id,
        prompt=record.prompt,
        timestamp=record.timestamp,
        engine=record.engine,
        latency_ms=record.result.latency_ms,
        ttft_ms=record.result.ttft_ms,
        tokens_generated=record.result.tokens_generated,
        duration_seconds=record.result.duration_seconds,
        prompt_tokens=record.result.prompt_tokens,
        prompt_eval_duration_seconds=record.result.prompt_eval_duration_seconds,
        throughput_tokens_per_second=record.throughput_tokens_per_second,
        success=record.success,
        error=record.error,
        resources=BenchmarkResourceResponse(
            cpu_percent=record.resources.cpu_percent,
            memory_percent=record.resources.memory_percent,
            memory_used_bytes=record.resources.memory_used_bytes,
            gpu_percent=record.resources.gpu_percent,
            gpu_memory_used_bytes=record.resources.gpu_memory_used_bytes,
        ),
    )


def _job_response(job: Job) -> BenchmarkJobResponse:
    return BenchmarkJobResponse(
        job_id=job.job_id,
        status=job.status,
        error=job.error,
    )


@router.get("", response_model=list[BenchmarkResponse])
def list_benchmarks(
    service: BenchmarkServiceDependency,
) -> list[BenchmarkResponse]:
    """Return all benchmark results."""

    return [_record_response(record) for record in service.list_records()]


@router.post(
    "",
    response_model=BenchmarkRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def run_benchmark(
    request: BenchmarkRunRequest,
    background_tasks: BackgroundTasks,
    _user: EngineerUserDependency,
    service: BenchmarkExecutionServiceDependency,
) -> BenchmarkRunResponse:
    """Run and persist a benchmark suite."""

    try:
        job = service.start(
            model=request.model,
            engine=request.engine,
            prompts=tuple(request.prompts),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(
        service.execute_job,
        job_id=job.job_id,
        model=request.model,
        engine=request.engine,
        prompts=tuple(request.prompts),
    )

    return BenchmarkRunResponse(
        job=_job_response(job),
        records=[],
        recommendation=None,
    )


@router.get(
    "/compare",
    response_model=BenchmarkReportResponse | None,
)
def compare_benchmarks(
    service: BenchmarkServiceDependency,
) -> BenchmarkReportResponse | None:
    """Return aggregate data for comparing benchmark results."""

    return get_benchmark_report(service)


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


@router.get("/{benchmark_id}", response_model=BenchmarkResponse)
def get_benchmark(
    benchmark_id: str,
    service: BenchmarkServiceDependency,
) -> BenchmarkResponse:
    """Return a single benchmark result."""

    record = service.get_record(benchmark_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark result not found.",
        )

    return _record_response(record)


def _recommend(records: tuple[BenchmarkRecord, ...]) -> str | None:
    if not records:
        return None

    average_ttft = sum(record.result.ttft_ms for record in records) / len(records)
    average_throughput = (
        sum(record.throughput_tokens_per_second for record in records) / len(records)
    )

    if average_ttft <= 1000 and average_throughput >= 10:
        return "The measured run is suitable for interactive chat workloads."

    if average_throughput >= 20:
        return "The measured run is better suited to batch throughput than low-latency chat."

    return "The measured run is resource constrained; compare another engine or a smaller model."
