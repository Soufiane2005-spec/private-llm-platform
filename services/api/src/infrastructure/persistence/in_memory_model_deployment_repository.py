"""In-memory model deployment repository."""

from domain.models.deployment import ModelDeployment


class InMemoryModelDeploymentRepository:
    """Store model deployments in memory by identifier."""

    def __init__(self) -> None:
        self._deployments: dict[str, ModelDeployment] = {}

    def save(self, deployment: ModelDeployment) -> None:
        """Store or replace a deployment."""

        self._deployments[deployment.deployment_id] = deployment

    def get(self, deployment_id: str) -> ModelDeployment | None:
        """Return a deployment by identifier."""

        return self._deployments.get(deployment_id)

    def list(self) -> tuple[ModelDeployment, ...]:
        """Return all deployments in deterministic order."""

        return tuple(
            self._deployments[deployment_id]
            for deployment_id in sorted(self._deployments)
        )

    def delete(self, deployment_id: str) -> None:
        """Delete a deployment if it exists."""

        self._deployments.pop(deployment_id, None)
