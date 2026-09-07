"""Prometheus-compatible platform metrics endpoint."""

from fastapi import APIRouter, Response

from domain.models.deployment import ModelDeploymentStatus
from infrastructure.monitoring.resource_provider import SystemResourceProvider
from infrastructure.persistence.factory import (
    get_persistent_benchmark_repository,
    get_persistent_deployment_repository,
    get_persistent_job_repository,
)

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=Response)
def metrics() -> Response:
    """Expose current platform gauges in Prometheus text format."""

    usage = SystemResourceProvider().get_system_usage()
    jobs = get_persistent_job_repository().list()
    deployments = get_persistent_deployment_repository().list()
    benchmarks = get_persistent_benchmark_repository().list()
    lines = [
        "# HELP private_llm_platform_cpu_percent Current host CPU usage percent.",
        "# TYPE private_llm_platform_cpu_percent gauge",
        f"private_llm_platform_cpu_percent {usage.cpu_percent}",
        "# HELP private_llm_platform_memory_percent Current host memory usage percent.",
        "# TYPE private_llm_platform_memory_percent gauge",
        f"private_llm_platform_memory_percent {usage.memory_percent}",
        "# HELP private_llm_platform_memory_used_bytes Current host memory usage bytes.",
        "# TYPE private_llm_platform_memory_used_bytes gauge",
        f"private_llm_platform_memory_used_bytes {usage.memory_used_bytes}",
        "# HELP private_llm_platform_jobs_total Jobs by status.",
        "# TYPE private_llm_platform_jobs_total gauge",
    ]

    if usage.gpu_percent is not None:
        lines.extend(
            [
                "# HELP private_llm_platform_gpu_percent Current GPU usage percent.",
                "# TYPE private_llm_platform_gpu_percent gauge",
                f"private_llm_platform_gpu_percent {usage.gpu_percent}",
            ]
        )
    if usage.gpu_memory_used_bytes is not None:
        lines.extend(
            [
                "# HELP private_llm_platform_gpu_memory_used_bytes Current GPU memory used bytes.",
                "# TYPE private_llm_platform_gpu_memory_used_bytes gauge",
                (
                    "private_llm_platform_gpu_memory_used_bytes "
                    f"{usage.gpu_memory_used_bytes}"
                ),
            ]
        )

    for status in ("pending", "running", "completed", "failed"):
        count = sum(1 for job in jobs if job.status.value == status)
        lines.append(f'private_llm_platform_jobs_total{{status="{status}"}} {count}')

    lines.extend(
        [
            "# HELP private_llm_platform_deployments_total Deployments by status.",
            "# TYPE private_llm_platform_deployments_total gauge",
        ]
    )
    for status in ModelDeploymentStatus:
        count = sum(1 for deployment in deployments if deployment.status is status)
        lines.append(
            f'private_llm_platform_deployments_total{{status="{status.value}"}} {count}'
        )

    lines.extend(
        [
            "# HELP private_llm_platform_benchmarks_total Stored benchmark records.",
            "# TYPE private_llm_platform_benchmarks_total gauge",
            f"private_llm_platform_benchmarks_total {len(benchmarks)}",
        ]
    )

    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
