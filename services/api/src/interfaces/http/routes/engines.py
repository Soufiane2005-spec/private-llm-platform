"""HTTP routes for LLM engine selection."""

from fastapi import APIRouter

from domain.models.llm_engine import (
    EngineSelectionRequest,
)
from domain.recommendations.engine_selector import (
    select_engine,
)
from interfaces.http.schemas.engine_selection import (
    EngineSelectionRequestSchema,
    EngineSelectionResponseSchema,
)

router = APIRouter(prefix="/engines", tags=["engines"])


@router.post(
    "/select",
    response_model=EngineSelectionResponseSchema,
)
def select_engine_endpoint(
    request: EngineSelectionRequestSchema,
) -> EngineSelectionResponseSchema:
    """Select the most appropriate LLM engine."""

    selection = select_engine(
        EngineSelectionRequest(
            nvidia_gpu_available=request.nvidia_gpu_available,
            required_capabilities=frozenset(
                request.required_capabilities,
            ),
            preferred_capabilities=frozenset(
                request.preferred_capabilities,
            ),
        ),
    )

    return EngineSelectionResponseSchema(
        engine=selection.engine.value,
        score=selection.score,
        matched_preferences=[
            capability.value
            for capability in selection.matched_preferences
        ],
        rationale=list(selection.rationale),
    )