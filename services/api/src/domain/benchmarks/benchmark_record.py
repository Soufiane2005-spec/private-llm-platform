"""Aggregated benchmark result domain model."""

from dataclasses import dataclass

from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    """Complete benchmark record for one prompt execution."""

    benchmark_id: str
    model_id: str
    result: BenchmarkResult
    resources: BenchmarkResourceMetrics

    def __post_init__(self) -> None:
        """Validate benchmark record invariants."""

        if not self.benchmark_id.strip():
            raise ValueError("benchmark_id cannot be empty.")

        if not self.model_id.strip():
            raise ValueError("model_id cannot be empty.")

    @property
    def engine(self) -> str:
        """Return the engine used for the benchmark."""
        return self.result.engine

    @property
    def prompt_id(self) -> str:
        """Return the benchmark prompt identifier."""
        return self.result.prompt_id

    @property
    def latency_ms(self) -> float:
        """Return benchmark latency."""
        return self.result.latency_ms

    @property
    def throughput_tokens_per_second(self) -> float:
        """Return benchmark throughput."""
        return self.result.throughput_tokens_per_second