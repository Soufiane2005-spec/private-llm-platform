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
            context_length=8192,
        ),
        ModelCatalogEntry(
            model_id="phi3-mini",
            display_name="Phi-3 Mini",
            engine=LLMEngine.OLLAMA,
            engine_model_id="phi3:mini",
            context_length=4096,
        ),
        ModelCatalogEntry(
            model_id="llama3.2-1b",
            display_name="Llama 3.2 1B",
            engine=LLMEngine.OLLAMA,
            engine_model_id="llama3.2:1b",
            context_length=8192,
        ),
        ModelCatalogEntry(
            model_id="gemma2-2b",
            display_name="Gemma 2 2B",
            engine=LLMEngine.OLLAMA,
            engine_model_id="gemma2:2b",
            context_length=8192,
        ),
        ModelCatalogEntry(
            model_id="tinyllama",
            display_name="TinyLlama",
            engine=LLMEngine.OLLAMA,
            engine_model_id="tinyllama",
            context_length=2048,
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
        ModelCatalogEntry(
            model_id="smollm2-360m",
            display_name="SmolLM2 360M",
            engine=LLMEngine.VLLM,
            engine_model_id="HuggingFaceTB/SmolLM2-360M-Instruct",
            context_length=1024,
            served_model_name="smollm2-360m",
            gpu_required=True,
        ),
        ModelCatalogEntry(
            model_id="qwen2.5-0.5b",
            display_name="Qwen2.5 0.5B Instruct",
            engine=LLMEngine.VLLM,
            engine_model_id="Qwen/Qwen2.5-0.5B-Instruct",
            context_length=1024,
            served_model_name="qwen2.5-0.5b",
            gpu_required=True,
        ),
        ModelCatalogEntry(
            model_id="tinyllama-1.1b-chat",
            display_name="TinyLlama 1.1B Chat",
            engine=LLMEngine.VLLM,
            engine_model_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            context_length=1024,
            served_model_name="tinyllama-1.1b-chat",
            gpu_required=True,
        ),
        ModelCatalogEntry(
            model_id="opt-125m",
            display_name="OPT 125M",
            engine=LLMEngine.VLLM,
            engine_model_id="facebook/opt-125m",
            context_length=1024,
            served_model_name="opt-125m",
            gpu_required=True,
        ),
    )
