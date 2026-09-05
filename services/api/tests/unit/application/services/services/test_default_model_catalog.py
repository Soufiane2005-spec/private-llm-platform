from application.services.default_model_catalog import (
    create_default_model_catalog,
)
from domain.models.llm_engine import LLMEngine


def test_default_catalog_contains_supported_models() -> None:
    catalog = create_default_model_catalog()

    models = catalog.list_models()

    assert tuple(model.model_id for model in models) == (
        "qwen2.5-1.5b",
        "qwen3-0.6b",
    )


def test_default_catalog_maps_models_to_expected_engines() -> None:
    catalog = create_default_model_catalog()

    qwen_ollama = catalog.get("qwen2.5-1.5b")
    qwen = catalog.get("qwen3-0.6b")

    assert qwen_ollama.engine is LLMEngine.OLLAMA
    assert qwen_ollama.engine_model_id == "qwen2.5:1.5b"

    assert qwen.engine is LLMEngine.VLLM
    assert qwen.engine_model_id == "Qwen/Qwen3-0.6B"
