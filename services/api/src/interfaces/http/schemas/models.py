"""HTTP schemas for model catalog endpoints."""

from pydantic import BaseModel

from domain.models.llm_engine import LLMEngine


class ModelResponse(BaseModel):
    """Public representation of a model catalog entry."""

    model_id: str
    display_name: str
    engine: LLMEngine
    engine_model_id: str
    context_length: int | None
    enabled: bool