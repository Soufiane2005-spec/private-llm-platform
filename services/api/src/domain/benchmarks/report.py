"""Domain model for benchmark reports."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    """Aggregated summary of benchmark executions."""

    benchmark_count: int
    average_latency_ms: float
    average_throughput_tokens_per_second: float
    average_cpu_percent: float
    average_memory_percent: float
    average_gpu_percent: float | None = None

    def __post_init__(self) -> None:
        """Validate benchmark report invariants."""

        if self.benchmark_count <= 0:
            raise ValueError("benchmark_count must be greater than zero.")

        if self.average_latency_ms < 0:
            raise ValueError("average_latency_ms cannot be negative.")

        if self.average_throughput_tokens_per_second < 0:
            raise ValueError(
                "average_throughput_tokens_per_second cannot be negative."
            )

        if not 0 <= self.average_cpu_percent <= 100:
            raise ValueError(
                "average_cpu_percent must be between 0 and 100."
            )

        if not 0 <= self.average_memory_percent <= 100:
            raise ValueError(
                "average_memory_percent must be between 0 and 100."
            )

        if (
            self.average_gpu_percent is not None
            and not 0 <= self.average_gpu_percent <= 100
        ):
            raise ValueError(
                "average_gpu_percent must be between 0 and 100."
            )