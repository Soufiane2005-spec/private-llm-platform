"""HTTP routes for model management."""

from fastapi import APIRouter

from application.services.default_model_catalog import create_default_model_catalog
from interfaces.http.schemas.models import ModelResponse

router = APIRouter(prefix="/models", tags=["models"])

_catalog = create_default_model_catalog()


@router.get("", response_model=list[ModelResponse])
def list_models() -> list[ModelResponse]:
    """Return all models available in the platform catalog."""

    return [
        ModelResponse(
            model_id=model.model_id,
            display_name=model.display_name,
            engine=model.engine,
            engine_model_id=model.engine_model_id,
            context_length=model.context_length,
            enabled=model.enabled,
        )
        for model in _catalog.list_models()
    ]