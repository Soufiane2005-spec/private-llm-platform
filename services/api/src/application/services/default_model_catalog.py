"""Default model catalog used by the management API."""

from application.services.model_catalog import ModelCatalog
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry


def create_default_model_catalog() -> ModelCatalog:
    """Create the catalog of models supported by the local platform."""

    return ModelCatalog(
        [
            ModelCatalogEntry(
                model_id="qwen2.5-1.5b",
                display_name="Qwen2.5 1.5B",
                engine=LLMEngine.OLLAMA,
                engine_model_id="qwen2.5:1.5b",
            ),
            ModelCatalogEntry(
                model_id="qwen3-0.6b",
                display_name="Qwen3 0.6B",
                engine=LLMEngine.VLLM,
                engine_model_id="Qwen/Qwen3-0.6B",
                context_length=1024,
            ),
        ]
    )
