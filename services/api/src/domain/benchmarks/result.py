"""Domain models for benchmark results."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Result produced by a single LLM benchmark execution."""

    prompt_id: str
    engine: str
    latency_ms: float
    ttft_ms: float = 0.0
    tokens_generated: int = 0
    duration_seconds: float = 0.0
    prompt_tokens: int | None = None
    prompt_eval_duration_seconds: float | None = None

    def __post_init__(self) -> None:
        """Validate benchmark result invariants."""

        if not self.prompt_id.strip():
            raise ValueError("prompt_id cannot be empty.")

        if not self.engine.strip():
            raise ValueError("engine cannot be empty.")

        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative.")

        if self.ttft_ms < 0:
            raise ValueError("ttft_ms cannot be negative.")

        if self.tokens_generated < 0:
            raise ValueError("tokens_generated cannot be negative.")

        if self.duration_seconds < 0:
            raise ValueError("duration_seconds cannot be negative.")

        if self.prompt_tokens is not None and self.prompt_tokens < 0:
            raise ValueError("prompt_tokens cannot be negative.")

        if (
            self.prompt_eval_duration_seconds is not None
            and self.prompt_eval_duration_seconds < 0
        ):
            raise ValueError("prompt_eval_duration_seconds cannot be negative.")

        if self.tokens_generated > 0 and self.duration_seconds <= 0:
            raise ValueError(
                "duration_seconds must be greater than zero "
                "when tokens are generated."
            )

    @property
    def throughput_tokens_per_second(self) -> float:
        """Return generated-token throughput."""

        if self.tokens_generated == 0:
            return 0.0

        return self.tokens_generated / self.duration_seconds
