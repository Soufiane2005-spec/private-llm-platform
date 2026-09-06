from application.services.default_model_catalog import default_model_catalog_entries
from domain.models.llm_engine import LLMEngine


def test_default_catalog_contains_supported_models() -> None:
    models = default_model_catalog_entries()

    assert tuple(model.model_id for model in models) == (
        "qwen2.5-1.5b",
        "smollm2-135m",
    )


def test_default_catalog_maps_models_to_expected_engines() -> None:
    qwen_ollama, smollm = default_model_catalog_entries()

    assert qwen_ollama.engine is LLMEngine.OLLAMA
    assert qwen_ollama.engine_model_id == "qwen2.5:1.5b"

    assert smollm.engine is LLMEngine.VLLM
    assert smollm.engine_model_id == "HuggingFaceTB/SmolLM2-135M-Instruct"
    assert smollm.served_model_name == "smollm2-135m"
