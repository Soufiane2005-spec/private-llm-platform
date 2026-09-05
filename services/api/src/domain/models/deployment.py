"""Domain models for deployed LLM runtimes."""

from dataclasses import dataclass, replace
from enum import StrEnum

from domain.models.llm_engine import LLMEngine


class ModelDeploymentStatus(StrEnum):
    """Runtime status exposed for model deployments."""

    STOPPED = "stopped"
    DEPLOYING = "deploying"
    LOADING = "loading"
    RUNNING = "running"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ModelDeployment:
    """A model runtime managed by the platform."""

    deployment_id: str
    model: str
    engine: LLMEngine
    status: ModelDeploymentStatus = ModelDeploymentStatus.STOPPED
    runtime_state: str = "not-created"
    error: str | None = None
    gpu_available: bool | None = None

    def __post_init__(self) -> None:
        """Validate deployment invariants."""

        if not self.deployment_id.strip():
            raise ValueError("deployment_id cannot be empty.")

        if not self.model.strip():
            raise ValueError("model cannot be empty.")

        if self.status is ModelDeploymentStatus.FAILED and not self.error:
            raise ValueError("failed deployments must contain an error.")

    def with_status(
        self,
        status: ModelDeploymentStatus,
        *,
        runtime_state: str,
        error: str | None = None,
        gpu_available: bool | None = None,
    ) -> "ModelDeployment":
        """Return a deployment with updated runtime information."""

        if status is ModelDeploymentStatus.FAILED and not error:
            raise ValueError("failed deployments must contain an error.")

        return replace(
            self,
            status=status,
            runtime_state=runtime_state,
            error=error,
            gpu_available=gpu_available,
        )
