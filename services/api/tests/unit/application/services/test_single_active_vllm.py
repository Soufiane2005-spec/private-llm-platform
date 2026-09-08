"""Tests for the single-active-vLLM deployment rule."""

import pytest

from application.services.model_deployment_service import (
    ModelDeploymentService,
    SingleActiveVllmError,
)
from domain.models.deployment import (
    ModelDeployment,
    ModelDeploymentStatus,
)
from domain.models.llm_engine import LLMEngine


class FakeDeploymentRepository:
    """Minimal deployment repository for service tests."""

    def __init__(
        self,
        deployments: list[ModelDeployment] | None = None,
    ) -> None:
        self.items = {
            deployment.deployment_id: deployment
            for deployment in (deployments or [])
        }

    def list(self) -> tuple[ModelDeployment, ...]:
        return tuple(self.items.values())

    def get(
        self,
        deployment_id: str,
    ) -> ModelDeployment | None:
        return self.items.get(deployment_id)

    def save(
        self,
        deployment: ModelDeployment,
    ) -> None:
        self.items[deployment.deployment_id] = deployment

    def delete(self, deployment_id: str) -> None:
        self.items.pop(deployment_id, None)


class FakeDeploymentManager:
    """Minimal deployment manager used by the application service."""

    def status(
        self,
        deployment: ModelDeployment,
    ) -> ModelDeployment:
        return deployment


class FakeJobs:
    """Minimal job submission fake."""

    def __init__(self) -> None:
        self.submitted: list[str] = []

    def submit(
        self,
        job_type: str,
        *,
        enqueue: bool,
    ):
        self.submitted.append(job_type)
        return object()


class FakeJobRepository:
    """Unused job repository fake for submission-only tests."""

    def get(self, job_id: str):
        return None

    def save(self, job) -> None:
        return None


def deployment(
    deployment_id: str,
    *,
    engine: LLMEngine,
    status: ModelDeploymentStatus,
) -> ModelDeployment:
    """Create a deployment fixture."""

    return ModelDeployment(
        deployment_id=deployment_id,
        model=deployment_id,
        engine=engine,
        status=status,
    )


def service_with(
    deployments: list[ModelDeployment],
) -> ModelDeploymentService:
    """Build a deployment service with in-memory fakes."""

    return ModelDeploymentService(
        deployments=FakeDeploymentRepository(deployments),
        manager=FakeDeploymentManager(),
        jobs=FakeJobs(),
        job_repository=FakeJobRepository(),
    )


@pytest.mark.parametrize(
    "active_status",
    [
        ModelDeploymentStatus.DEPLOYING,
        ModelDeploymentStatus.LOADING,
        ModelDeploymentStatus.RUNNING,
    ],
)
def test_deploy_rejects_second_active_vllm(
    active_status: ModelDeploymentStatus,
) -> None:
    """A second active vLLM cannot be submitted."""

    service = service_with(
        [
            deployment(
                "vllm-active",
                engine=LLMEngine.VLLM,
                status=active_status,
            )
        ]
    )

    with pytest.raises(
        SingleActiveVllmError,
        match=(
            "Another vLLM model is already active. "
            "Stop it before deploying this model."
        ),
    ):
        service.deploy(
            model="second-vllm",
            engine=LLMEngine.VLLM,
        )


def test_stopped_vllm_does_not_block_new_vllm() -> None:
    """A stopped vLLM releases the GPU slot."""

    service = service_with(
        [
            deployment(
                "vllm-stopped",
                engine=LLMEngine.VLLM,
                status=ModelDeploymentStatus.STOPPED,
            )
        ]
    )

    created, _job = service.deploy(
        model="second-vllm",
        engine=LLMEngine.VLLM,
    )

    assert created.engine is LLMEngine.VLLM
    assert created.status is ModelDeploymentStatus.DEPLOYING


def test_active_ollama_does_not_block_vllm() -> None:
    """Ollama is independent from the single vLLM GPU slot."""

    service = service_with(
        [
            deployment(
                "ollama-active",
                engine=LLMEngine.OLLAMA,
                status=ModelDeploymentStatus.RUNNING,
            )
        ]
    )

    created, _job = service.deploy(
        model="vllm-model",
        engine=LLMEngine.VLLM,
    )

    assert created.engine is LLMEngine.VLLM


def test_active_vllm_does_not_block_ollama() -> None:
    """An active vLLM never prevents Ollama deployment."""

    service = service_with(
        [
            deployment(
                "vllm-active",
                engine=LLMEngine.VLLM,
                status=ModelDeploymentStatus.RUNNING,
            )
        ]
    )

    created, _job = service.deploy(
        model="llama3.2:1b",
        engine=LLMEngine.OLLAMA,
    )

    assert created.engine is LLMEngine.OLLAMA


def test_start_rejects_vllm_when_another_is_active() -> None:
    """Starting a stopped vLLM is blocked by another active vLLM."""

    service = service_with(
        [
            deployment(
                "vllm-active",
                engine=LLMEngine.VLLM,
                status=ModelDeploymentStatus.RUNNING,
            ),
            deployment(
                "vllm-stopped",
                engine=LLMEngine.VLLM,
                status=ModelDeploymentStatus.STOPPED,
            ),
        ]
    )

    with pytest.raises(SingleActiveVllmError):
        service.start("vllm-stopped")


def test_restart_ignores_the_target_deployment_itself() -> None:
    """A vLLM can restart without conflicting with itself."""

    service = service_with(
        [
            deployment(
                "vllm-active",
                engine=LLMEngine.VLLM,
                status=ModelDeploymentStatus.RUNNING,
            )
        ]
    )

    restarted, _job = service.restart("vllm-active")

    assert restarted.status is ModelDeploymentStatus.LOADING
    assert restarted.runtime_state == "restart-job-submitted"