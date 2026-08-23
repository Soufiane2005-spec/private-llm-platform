"""Domain models for benchmark results."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Result produced by a single LLM benchmark execution."""

    prompt_id: str
    engine: str
    latency_ms: float

    def __post_init__(self) -> None:
        """Validate benchmark result invariants."""

        if not self.prompt_id.strip():
            raise ValueError("prompt_id cannot be empty.")

        if not self.engine.strip():
            raise ValueError("engine cannot be empty.")

        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative.")