import pytest

from application.services.model_catalog import (
    DuplicateModelError,
    ModelCatalog,
    ModelNotFoundError,
)
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry
from infrastructure.persistence.in_memory_model_catalog_repository import (
    InMemoryModelCatalogRepository,
)


def make_model(
    model_id: str = "smollm2-135m",
) -> ModelCatalogEntry:
    return ModelCatalogEntry(
        model_id=model_id,
        display_name="SmolLM2 135M",
        engine=LLMEngine.VLLM,
        engine_model_id="HuggingFaceTB/SmolLM2-135M-Instruct",
        context_length=1024,
        served_model_name="smollm2-135m",
        gpu_required=True,
    )


def test_add_and_get_model() -> None:
    catalog = ModelCatalog(repository=InMemoryModelCatalogRepository())

    model = make_model()

    catalog.add(model)

    assert catalog.get("smollm2-135m") == model


def test_list_models_returns_deterministic_order() -> None:
    repository = InMemoryModelCatalogRepository()
    catalog = ModelCatalog(repository=repository)
    catalog.add(make_model("z-model"))
    catalog.add(make_model("a-model"))

    result = catalog.list_models()

    assert tuple(model.model_id for model in result) == (
        "a-model",
        "z-model",
    )


def test_reject_duplicate_model_id() -> None:
    model = make_model()
    catalog = ModelCatalog(repository=InMemoryModelCatalogRepository())
    catalog.add(model)

    with pytest.raises(
        DuplicateModelError,
        match="already exists",
    ):
        catalog.add(model)


def test_raise_error_when_model_not_found() -> None:
    catalog = ModelCatalog(repository=InMemoryModelCatalogRepository())

    with pytest.raises(
        ModelNotFoundError,
        match="was not found",
    ):
        catalog.get("missing-model")
