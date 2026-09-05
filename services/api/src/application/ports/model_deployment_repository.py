"""Repository port for model deployments."""

from typing import Protocol

from domain.models.deployment import ModelDeployment


class ModelDeploymentRepository(Protocol):
    """Persist and retrieve model deployments."""

    def save(self, deployment: ModelDeployment) -> None:
        """Store or replace a deployment."""

    def get(self, deployment_id: str) -> ModelDeployment | None:
        """Return one deployment by identifier."""

    def list(self) -> tuple[ModelDeployment, ...]:
        """Return all deployments."""

    def delete(self, deployment_id: str) -> None:
        """Delete one deployment if it exists."""
