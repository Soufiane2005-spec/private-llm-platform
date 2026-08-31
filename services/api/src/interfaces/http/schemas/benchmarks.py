"""HTTP schemas for benchmark endpoints."""

from pydantic import BaseModel


class BenchmarkResourceResponse(BaseModel):
    """Resource metrics captured during a benchmark."""

    cpu_percent: float
    memory_percent: float
    memory_used_bytes: int
    gpu_percent: float | None
    gpu_memory_used_bytes: int | None


class BenchmarkResponse(BaseModel):
    """Public representation of one benchmark record."""

    benchmark_id: str
    model_id: str
    prompt_id: str
    engine: str
    latency_ms: float
    tokens_generated: int
    duration_seconds: float
    throughput_tokens_per_second: float
    resources: BenchmarkResourceResponse


class BenchmarkReportResponse(BaseModel):
    """Aggregated benchmark report."""

    benchmark_count: int
    average_latency_ms: float
    average_throughput_tokens_per_second: float
    average_cpu_percent: float
    average_memory_percent: float
    average_gpu_percent: float | None