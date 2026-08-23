"""Domain models for benchmark prompts."""

from dataclasses import dataclass
from enum import StrEnum


class PromptCategory(StrEnum):
    """Supported benchmark prompt categories."""

    SHORT = "short"
    REASONING = "reasoning"
    GENERATION = "generation"
    CODE = "code"


@dataclass(frozen=True, slots=True)
class BenchmarkPrompt:
    """Prompt used to benchmark an LLM engine."""

    prompt_id: str
    category: PromptCategory
    text: str

    def __post_init__(self) -> None:
        """Validate benchmark prompt invariants."""

        if not self.prompt_id.strip():
            raise ValueError("prompt_id cannot be empty.")

        if not self.text.strip():
            raise ValueError("prompt text cannot be empty.")