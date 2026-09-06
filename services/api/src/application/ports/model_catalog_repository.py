"""Repository port for model catalog persistence."""

from typing import Protocol

from domain.models.model_catalog import ModelCatalogEntry


class ModelCatalogRepository(Protocol):
    """Persist and retrieve model catalog entries."""

    def save(self, model: ModelCatalogEntry) -> None:
        """Store or replace a model catalog entry."""

    def get(self, model_id: str) -> ModelCatalogEntry | None:
        """Return one model by platform identifier."""

    def list(self) -> tuple[ModelCatalogEntry, ...]:
        """Return all model catalog entries."""

    def delete(self, model_id: str) -> None:
        """Delete one model catalog entry if it exists."""
