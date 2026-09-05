"""Runtime manager port for model deployments."""

from typing import Protocol

from domain.models.deployment import ModelDeployment


class ModelDeploymentManager(Protocol):
    """Control the runtime lifecycle of model deployments."""

    def deploy(self, deployment: ModelDeployment) -> ModelDeployment:
        """Create or update the runtime deployment."""

    def start(self, deployment: ModelDeployment) -> ModelDeployment:
        """Start a stopped deployment."""

    def stop(self, deployment: ModelDeployment) -> ModelDeployment:
        """Stop a running deployment."""

    def restart(self, deployment: ModelDeployment) -> ModelDeployment:
        """Restart a deployment."""

    def delete(self, deployment: ModelDeployment) -> None:
        """Remove runtime resources for a deployment."""
