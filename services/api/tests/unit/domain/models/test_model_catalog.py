import pytest

from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry


def test_create_model_catalog_entry() -> None:
    entry = ModelCatalogEntry(
        model_id="llama-3.2-1b",
        display_name="Llama 3.2 1B",
        engine=LLMEngine.OLLAMA,
        engine_model_id="llama3.2:1b",
        context_length=131072,
    )

    assert entry.model_id == "llama-3.2-1b"
    assert entry.engine is LLMEngine.OLLAMA
    assert entry.engine_model_id == "llama3.2:1b"
    assert entry.enabled is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_id", ""),
        ("display_name", ""),
        ("engine_model_id", ""),
    ],
)
def test_reject_empty_required_fields(
    field: str,
    value: str,
) -> None:
    values = {
        "model_id": "qwen3-0.6b",
        "display_name": "Qwen3 0.6B",
        "engine": LLMEngine.VLLM,
        "engine_model_id": "Qwen/Qwen3-0.6B",
    }
    values[field] = value

    with pytest.raises(ValueError):
        ModelCatalogEntry(**values)


def test_reject_invalid_context_length() -> None:
    with pytest.raises(
        ValueError,
        match="context_length must be greater than zero",
    ):
        ModelCatalogEntry(
            model_id="qwen3-0.6b",
            display_name="Qwen3 0.6B",
            engine=LLMEngine.VLLM,
            engine_model_id="Qwen/Qwen3-0.6B",
            context_length=0,
        )