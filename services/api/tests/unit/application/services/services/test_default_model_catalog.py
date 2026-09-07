from application.services.default_model_catalog import default_model_catalog_entries
from domain.models.llm_engine import LLMEngine


def test_default_catalog_contains_supported_models() -> None:
    models = default_model_catalog_entries()

    assert tuple(model.model_id for model in models) == (
        "qwen2.5-1.5b",
        "phi3-mini",
        "llama3.2-1b",
        "gemma2-2b",
        "tinyllama",
        "smollm2-135m",
        "smollm2-360m",
        "qwen2.5-0.5b",
        "tinyllama-1.1b-chat",
        "opt-125m",
    )


def test_default_catalog_maps_models_to_expected_engines() -> None:
    models = default_model_catalog_entries()
    by_id = {model.model_id: model for model in models}

    assert sum(model.engine is LLMEngine.OLLAMA for model in models) == 5
    assert sum(model.engine is LLMEngine.VLLM for model in models) == 5
    assert by_id["qwen2.5-1.5b"].engine_model_id == "qwen2.5:1.5b"
    assert by_id["phi3-mini"].engine_model_id == "phi3:mini"

    smollm = by_id["smollm2-135m"]
    assert smollm.engine is LLMEngine.VLLM
    assert smollm.engine_model_id == "HuggingFaceTB/SmolLM2-135M-Instruct"
    assert smollm.served_model_name == "smollm2-135m"
    assert by_id["qwen2.5-0.5b"].served_model_name == "qwen2.5-0.5b"
