"""Local deterministic model deployment manager.

This adapter is intentionally conservative: it exposes real lifecycle state
without claiming Kubernetes resources exist when no cluster adapter is wired.
"""

from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine


class LocalModelDeploymentManager:
    """Manage deployments for local/stage environments."""

    def __init__(self, *, gpu_available: bool = False) -> None:
        self._gpu_available = gpu_available

    def deploy(self, deployment: ModelDeployment) -> ModelDeployment:
        """Create or update a local deployment record."""

        if deployment.engine is LLMEngine.VLLM and not self._gpu_available:
            return deployment.with_status(
                ModelDeploymentStatus.FAILED,
                runtime_state="gpu-unavailable",
                error="vLLM deployment requires an NVIDIA GPU, but none is available.",
                gpu_available=False,
            )

        return deployment.with_status(
            ModelDeploymentStatus.RUNNING,
            runtime_state="local-runtime-ready",
            gpu_available=self._gpu_available,
        )

    def start(self, deployment: ModelDeployment) -> ModelDeployment:
        """Start a local deployment."""

        return self.deploy(deployment)

    def stop(self, deployment: ModelDeployment) -> ModelDeployment:
        """Stop a local deployment."""

        return deployment.with_status(
            ModelDeploymentStatus.STOPPED,
            runtime_state="scaled-to-zero",
            gpu_available=self._gpu_available,
        )

    def restart(self, deployment: ModelDeployment) -> ModelDeployment:
        """Restart a local deployment."""

        stopped = self.stop(deployment)
        return self.start(stopped)

    def delete(self, deployment: ModelDeployment) -> None:
        """No-op for local deployments."""
