"""Default model catalog entries used by the management API."""

from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry


def default_model_catalog_entries() -> tuple[ModelCatalogEntry, ...]:
    """Return the default models supported by the local platform."""

    return (
            ModelCatalogEntry(
                model_id="qwen2.5-1.5b",
                display_name="Qwen2.5 1.5B",
                engine=LLMEngine.OLLAMA,
                engine_model_id="qwen2.5:1.5b",
            ),
            ModelCatalogEntry(
                model_id="smollm2-135m",
                display_name="SmolLM2 135M",
                engine=LLMEngine.VLLM,
                engine_model_id="HuggingFaceTB/SmolLM2-135M-Instruct",
                context_length=1024,
                served_model_name="smollm2-135m",
                gpu_required=True,
            ),
    )
