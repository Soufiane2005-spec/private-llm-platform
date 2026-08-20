"""Application service for managing the LLM model catalog."""

from collections.abc import Iterable

from domain.models.model_catalog import ModelCatalogEntry


class ModelNotFoundError(LookupError):
    """Raised when a requested model does not exist in the catalog."""


class DuplicateModelError(ValueError):
    """Raised when the catalog contains duplicate model identifiers."""


class ModelCatalog:
    """In-memory catalog of models supported by the platform."""

    def __init__(self, entries: Iterable[ModelCatalogEntry] = ()) -> None:
        self._entries: dict[str, ModelCatalogEntry] = {}

        for entry in entries:
            self.add(entry)

    def add(self, entry: ModelCatalogEntry) -> None:
        """Add a model to the catalog."""

        if entry.model_id in self._entries:
            raise DuplicateModelError(
                f"Model '{entry.model_id}' already exists in the catalog."
            )

        self._entries[entry.model_id] = entry

    def list_models(self) -> tuple[ModelCatalogEntry, ...]:
        """Return every model in deterministic order."""

        return tuple(
            self._entries[model_id]
            for model_id in sorted(self._entries)
        )

    def get(self, model_id: str) -> ModelCatalogEntry:
        """Return one model by its platform identifier."""

        try:
            return self._entries[model_id]
        except KeyError as exc:
            raise ModelNotFoundError(
                f"Model '{model_id}' was not found in the catalog."
            ) from exc