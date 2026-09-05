"""Benchmark executor port."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BenchmarkExecution:
    """Low-level benchmark execution measurements."""

    total_latency_ms: float
    ttft_ms: float
    tokens_generated: int
    duration_seconds: float


class BenchmarkExecutor(Protocol):
    """Execute one prompt against a model runtime."""

    def execute(self, *, model: str, prompt: str) -> BenchmarkExecution:
        """Run a prompt and return measured performance."""
