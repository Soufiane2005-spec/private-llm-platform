"""In-memory model catalog repository."""

from domain.models.model_catalog import ModelCatalogEntry


class InMemoryModelCatalogRepository:
    """Store model catalog entries in memory by identifier."""

    def __init__(self) -> None:
        self._models: dict[str, ModelCatalogEntry] = {}

    def save(self, model: ModelCatalogEntry) -> None:
        """Store or replace a model catalog entry."""

        self._models[model.model_id] = model

    def get(self, model_id: str) -> ModelCatalogEntry | None:
        """Return one model by platform identifier."""

        return self._models.get(model_id)

    def list(self) -> tuple[ModelCatalogEntry, ...]:
        """Return all models in deterministic order."""

        return tuple(self._models[model_id] for model_id in sorted(self._models))

    def delete(self, model_id: str) -> None:
        """Delete one model if it exists."""

        self._models.pop(model_id, None)
