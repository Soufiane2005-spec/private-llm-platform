"""Route deployment operations to managers by inference engine."""

from application.ports.model_deployment_manager import ModelDeploymentManager
from domain.models.deployment import ModelDeployment
from domain.models.llm_engine import LLMEngine


class RoutedModelDeploymentManager:
    """Delegate deployment lifecycle operations to engine-specific managers."""

    def __init__(
        self,
        *,
        ollama_manager: ModelDeploymentManager,
        vllm_manager: ModelDeploymentManager,
    ) -> None:
        self._ollama_manager = ollama_manager
        self._vllm_manager = vllm_manager

    def deploy(self, deployment: ModelDeployment) -> ModelDeployment:
        """Create or update a runtime deployment."""

        return self._manager_for(deployment).deploy(deployment)

    def start(self, deployment: ModelDeployment) -> ModelDeployment:
        """Start a stopped deployment."""

        return self._manager_for(deployment).start(deployment)

    def stop(self, deployment: ModelDeployment) -> ModelDeployment:
        """Stop a running deployment."""

        return self._manager_for(deployment).stop(deployment)

    def restart(self, deployment: ModelDeployment) -> ModelDeployment:
        """Restart a deployment."""

        return self._manager_for(deployment).restart(deployment)

    def delete(self, deployment: ModelDeployment) -> None:
        """Remove runtime resources for a deployment."""

        self._manager_for(deployment).delete(deployment)

    def status(self, deployment: ModelDeployment) -> ModelDeployment:
        """Return current runtime status for a deployment."""

        return self._manager_for(deployment).status(deployment)

    def _manager_for(self, deployment: ModelDeployment) -> ModelDeploymentManager:
        if deployment.engine is LLMEngine.OLLAMA:
            return self._ollama_manager

        return self._vllm_manager
