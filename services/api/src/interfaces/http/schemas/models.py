"""HTTP schemas for model catalog endpoints."""

from pydantic import BaseModel, Field, model_validator

from domain.models.llm_engine import LLMEngine


class ModelCreateRequest(BaseModel):
    """Request payload for model catalog creation."""

    model_id: str | None = Field(default=None, min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=160)
    engine: LLMEngine
    engine_model_id: str = Field(min_length=1, max_length=240)
    context_length: int | None = Field(default=None, gt=0)
    enabled: bool = True
    served_model_name: str | None = Field(default=None, min_length=1, max_length=160)
    gpu_required: bool = False

    @model_validator(mode="after")
    def validate_engine_fields(self) -> "ModelCreateRequest":
        """Validate model fields that depend on the selected engine."""

        if self.engine is LLMEngine.OLLAMA and self.served_model_name is not None:
            raise ValueError("Ollama models cannot define served_model_name.")

        if self.engine is LLMEngine.VLLM and self.served_model_name is None:
            raise ValueError("vLLM models require served_model_name.")

        return self


class ModelUpdateRequest(BaseModel):
    """Request payload for model catalog updates."""

    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    engine_model_id: str | None = Field(default=None, min_length=1, max_length=240)
    context_length: int | None = Field(default=None, gt=0)
    enabled: bool | None = None
    served_model_name: str | None = Field(default=None, min_length=1, max_length=160)
    gpu_required: bool | None = None


class ModelResponse(BaseModel):
    """Public representation of a model catalog entry."""

    model_id: str
    display_name: str
    engine: LLMEngine
    engine_model_id: str
    context_length: int | None
    enabled: bool
    served_model_name: str | None
    gpu_required: bool
    runtime_available: bool
    benchmark_model_id: str
