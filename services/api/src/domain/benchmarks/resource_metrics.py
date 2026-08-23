"""Domain models for benchmark resource metrics."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenchmarkResourceMetrics:
    """CPU, memory, and GPU metrics captured during a benchmark."""

    cpu_percent: float
    memory_percent: float
    memory_used_bytes: int
    gpu_percent: float | None = None
    gpu_memory_used_bytes: int | None = None

    def __post_init__(self) -> None:
        """Validate benchmark resource metrics."""

        if not 0 <= self.cpu_percent <= 100:
            raise ValueError("cpu_percent must be between 0 and 100.")

        if not 0 <= self.memory_percent <= 100:
            raise ValueError("memory_percent must be between 0 and 100.")

        if self.memory_used_bytes < 0:
            raise ValueError("memory_used_bytes cannot be negative.")

        if self.gpu_percent is not None and not 0 <= self.gpu_percent <= 100:
            raise ValueError("gpu_percent must be between 0 and 100.")

        if (
            self.gpu_memory_used_bytes is not None
            and self.gpu_memory_used_bytes < 0
        ):
            raise ValueError(
                "gpu_memory_used_bytes cannot be negative."
            )