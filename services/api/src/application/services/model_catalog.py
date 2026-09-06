"""Application service for managing the LLM model catalog."""

from dataclasses import replace

from application.ports.model_catalog_repository import ModelCatalogRepository
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry

_UNSET = object()


class ModelNotFoundError(LookupError):
    """Raised when a requested model does not exist in the catalog."""


class DuplicateModelError(ValueError):
    """Raised when the catalog contains duplicate model identifiers."""


class ModelInUseError(ValueError):
    """Raised when deleting a model that still has a runtime deployment."""


class ModelCatalog:
    """Catalog of models supported by the platform."""

    def __init__(self, repository: ModelCatalogRepository) -> None:
        self._repository = repository

    def add(self, entry: ModelCatalogEntry) -> ModelCatalogEntry:
        """Add a model to the catalog."""

        self._validate_entry(entry)

        if self._repository.get(entry.model_id) is not None:
            raise DuplicateModelError(
                f"Model '{entry.model_id}' already exists in the catalog."
            )

        self._repository.save(entry)
        return entry

    def update(
        self,
        model_id: str,
        *,
        display_name: str | None | object = _UNSET,
        engine_model_id: str | None | object = _UNSET,
        context_length: int | None | object = _UNSET,
        enabled: bool | None | object = _UNSET,
        served_model_name: str | None | object = _UNSET,
        gpu_required: bool | None | object = _UNSET,
    ) -> ModelCatalogEntry:
        """Update a model catalog entry."""

        current = self.get(model_id)
        updated = replace(
            current,
            display_name=(
                display_name.strip()
                if isinstance(display_name, str)
                else current.display_name
            ),
            engine_model_id=(
                engine_model_id.strip()
                if isinstance(engine_model_id, str)
                else current.engine_model_id
            ),
            context_length=(
                current.context_length
                if context_length is _UNSET
                else context_length
            ),
            enabled=current.enabled if enabled is _UNSET else enabled,
            served_model_name=(
                served_model_name.strip()
                if isinstance(served_model_name, str)
                else None
                if served_model_name is None
                else current.served_model_name
            ),
            gpu_required=(
                current.gpu_required
                if gpu_required is _UNSET
                else gpu_required
            ),
        )
        self._validate_entry(updated)
        self._repository.save(updated)
        return updated

    def delete(self, model_id: str) -> None:
        """Delete a model catalog entry."""

        self.get(model_id)
        self._repository.delete(model_id)

    def list_models(self) -> tuple[ModelCatalogEntry, ...]:
        """Return every model in deterministic order."""

        return self._repository.list()

    def get(self, model_id: str) -> ModelCatalogEntry:
        """Return one model by its platform identifier."""

        entry = self._repository.get(model_id)

        if entry is None:
            raise ModelNotFoundError(
                f"Model '{model_id}' was not found in the catalog."
            )

        return entry

    @staticmethod
    def _validate_entry(entry: ModelCatalogEntry) -> None:
        if entry.engine is LLMEngine.OLLAMA and entry.served_model_name:
            raise ValueError("Ollama models cannot define a served_model_name.")

        if entry.engine is LLMEngine.VLLM and not entry.served_model_name:
            raise ValueError("vLLM models require a served_model_name.")
