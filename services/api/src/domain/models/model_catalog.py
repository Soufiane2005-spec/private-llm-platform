"""Domain models for the LLM model catalog."""

from dataclasses import dataclass

from domain.models.llm_engine import LLMEngine


@dataclass(frozen=True, slots=True)
class ModelCatalogEntry:
    """A model known and supported by the platform."""

    model_id: str
    display_name: str
    engine: LLMEngine
    engine_model_id: str
    context_length: int | None = None
    enabled: bool = True
    served_model_name: str | None = None
    gpu_required: bool = False

    def __post_init__(self) -> None:
        """Validate catalog entry invariants."""

        if not self.model_id.strip():
            raise ValueError("model_id cannot be empty.")

        if not self.display_name.strip():
            raise ValueError("display_name cannot be empty.")

        if not self.engine_model_id.strip():
            raise ValueError("engine_model_id cannot be empty.")

        if self.context_length is not None and self.context_length <= 0:
            raise ValueError("context_length must be greater than zero.")

        if self.served_model_name is not None and not self.served_model_name.strip():
            raise ValueError("served_model_name cannot be empty.")

        if self.engine is LLMEngine.VLLM and not self.served_model_name:
            raise ValueError("vLLM models require a served_model_name.")

    @property
    def benchmark_model_id(self) -> str:
        """Return the runtime model identifier used for benchmark execution."""

        return self.served_model_name or self.engine_model_id
