import pytest

from application.services.model_catalog import (
    DuplicateModelError,
    ModelCatalog,
    ModelNotFoundError,
)
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry


def make_model(
    model_id: str = "qwen3-0.6b",
) -> ModelCatalogEntry:
    return ModelCatalogEntry(
        model_id=model_id,
        display_name="Qwen3 0.6B",
        engine=LLMEngine.VLLM,
        engine_model_id="Qwen/Qwen3-0.6B",
        context_length=1024,
    )


def test_add_and_get_model() -> None:
    catalog = ModelCatalog()

    model = make_model()

    catalog.add(model)

    assert catalog.get("qwen3-0.6b") == model


def test_list_models_returns_deterministic_order() -> None:
    catalog = ModelCatalog(
        [
            make_model("z-model"),
            make_model("a-model"),
        ]
    )

    result = catalog.list_models()

    assert tuple(model.model_id for model in result) == (
        "a-model",
        "z-model",
    )


def test_reject_duplicate_model_id() -> None:
    model = make_model()
    catalog = ModelCatalog([model])

    with pytest.raises(
        DuplicateModelError,
        match="already exists",
    ):
        catalog.add(model)


def test_raise_error_when_model_not_found() -> None:
    catalog = ModelCatalog()

    with pytest.raises(
        ModelNotFoundError,
        match="was not found",
    ):
        catalog.get("missing-model")