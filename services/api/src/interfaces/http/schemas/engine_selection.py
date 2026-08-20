"""HTTP schemas for engine selection."""

from pydantic import BaseModel

from domain.models.llm_engine import EngineCapability


class EngineSelectionRequestSchema(BaseModel):
    """Request body for engine selection."""

    nvidia_gpu_available: bool
    required_capabilities: list[EngineCapability] = []
    preferred_capabilities: list[EngineCapability] = []

class EngineSelectionResponseSchema(BaseModel):
    """Engine selection response."""

    engine: str
    score: int
    matched_preferences: list[str]
    rationale: list[str]