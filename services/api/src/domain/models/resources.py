"""Domain models for runtime resource monitoring."""

from dataclasses import dataclass
from enum import StrEnum

from domain.models.llm_engine import LLMEngine


class EngineRuntimeState(StrEnum):
    """Runtime availability state of an LLM engine."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SystemResourceUsage:
    """Current CPU, memory, and GPU resource usage."""

    cpu_percent: float
    memory_percent: float
    memory_used_bytes: int
    memory_total_bytes: int
    gpu_percent: float | None = None
    gpu_memory_used_bytes: int | None = None
    gpu_memory_total_bytes: int | None = None

    def __post_init__(self) -> None:
        """Validate resource metrics."""

        if not 0 <= self.cpu_percent <= 100:
            raise ValueError("cpu_percent must be between 0 and 100.")

        if not 0 <= self.memory_percent <= 100:
            raise ValueError("memory_percent must be between 0 and 100.")

        if self.memory_used_bytes < 0:
            raise ValueError("memory_used_bytes cannot be negative.")

        if self.memory_total_bytes <= 0:
            raise ValueError("memory_total_bytes must be greater than zero.")

        if self.gpu_percent is not None and not 0 <= self.gpu_percent <= 100:
            raise ValueError("gpu_percent must be between 0 and 100.")


@dataclass(frozen=True, slots=True)
class EngineRuntimeStatus:
    """Current runtime status of an LLM engine."""

    engine: LLMEngine
    state: EngineRuntimeState
    detail: str | None = None