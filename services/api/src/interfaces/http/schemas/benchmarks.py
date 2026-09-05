"""HTTP schemas for benchmark endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field

from domain.jobs.job import JobStatus
from domain.models.llm_engine import LLMEngine


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
    prompt: str
    timestamp: datetime
    engine: str
    latency_ms: float
    ttft_ms: float
    tokens_generated: int
    duration_seconds: float
    prompt_tokens: int | None
    prompt_eval_duration_seconds: float | None
    throughput_tokens_per_second: float
    success: bool
    error: str | None
    resources: BenchmarkResourceResponse


class BenchmarkReportResponse(BaseModel):
    """Aggregated benchmark report."""

    benchmark_count: int
    average_latency_ms: float
    average_throughput_tokens_per_second: float
    average_cpu_percent: float
    average_memory_percent: float
    average_gpu_percent: float | None


class BenchmarkRunRequest(BaseModel):
    """Request payload for benchmark execution."""

    model: str = Field(min_length=1, max_length=200)
    engine: LLMEngine
    prompts: list[str] = Field(min_length=1, max_length=20)


class BenchmarkJobResponse(BaseModel):
    """Job summary returned for benchmark execution."""

    job_id: str
    status: JobStatus
    error: str | None


class BenchmarkRunResponse(BaseModel):
    """Benchmark execution response."""

    job: BenchmarkJobResponse
    records: list[BenchmarkResponse]
    recommendation: str | None
