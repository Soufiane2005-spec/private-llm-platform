from application.services.default_model_catalog import (
    create_default_model_catalog,
)
from domain.models.llm_engine import LLMEngine


def test_default_catalog_contains_supported_models() -> None:
    catalog = create_default_model_catalog()

    models = catalog.list_models()

    assert tuple(model.model_id for model in models) == (
        "llama-3.2-1b",
        "qwen3-0.6b",
    )


def test_default_catalog_maps_models_to_expected_engines() -> None:
    catalog = create_default_model_catalog()

    llama = catalog.get("llama-3.2-1b")
    qwen = catalog.get("qwen3-0.6b")

    assert llama.engine is LLMEngine.OLLAMA
    assert llama.engine_model_id == "llama3.2:1b"

    assert qwen.engine is LLMEngine.VLLM
    assert qwen.engine_model_id == "Qwen/Qwen3-0.6B"