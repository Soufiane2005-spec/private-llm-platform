"""Tests for model deployment concurrency rules."""

import pytest

from application.services.model_deployment_service import (
    DuplicateActiveDeploymentError,
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

    def delete(
        self,
        deployment_id: str,
    ) -> None:
        self.items.pop(
            deployment_id,
            None,
        )


class FakeDeploymentManager:
    """Minimal deployment manager used by the service."""

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
    """Unused job repository fake."""

    def get(
        self,
        job_id: str,
    ):
        return None

    def save(
        self,
        job,
    ) -> None:
        return None


def deployment(
    deployment_id: str,
    *,
    engine: LLMEngine,
    status: ModelDeploymentStatus,
    model: str | None = None,
) -> ModelDeployment:
    """Create a deployment fixture."""

    return ModelDeployment(
        deployment_id=deployment_id,
        model=(
            deployment_id
            if model is None
            else model
        ),
        engine=engine,
        status=status,
    )


def service_with(
    deployments: list[ModelDeployment],
) -> ModelDeploymentService:
    """Build a deployment service with in-memory fakes."""

    return ModelDeploymentService(
        deployments=FakeDeploymentRepository(
            deployments
        ),
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
    assert (
        created.status
        is ModelDeploymentStatus.DEPLOYING
    )


def test_active_ollama_does_not_block_vllm() -> None:
    """Ollama is independent from the vLLM GPU slot."""

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
    """An active vLLM does not block an Ollama model."""

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
    """Starting vLLM is blocked by another active vLLM."""

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

    with pytest.raises(
        SingleActiveVllmError
    ):
        service.start(
            "vllm-stopped"
        )


def test_restart_ignores_target_vllm_itself() -> None:
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

    restarted, _job = service.restart(
        "vllm-active"
    )

    assert (
        restarted.status
        is ModelDeploymentStatus.LOADING
    )
    assert (
        restarted.runtime_state
        == "restart-job-submitted"
    )


@pytest.mark.parametrize(
    "active_status",
    [
        ModelDeploymentStatus.DEPLOYING,
        ModelDeploymentStatus.LOADING,
        ModelDeploymentStatus.RUNNING,
    ],
)
def test_deploy_rejects_duplicate_active_ollama_model(
    active_status: ModelDeploymentStatus,
) -> None:
    """The same active Ollama model cannot be deployed twice."""

    service = service_with(
        [
            deployment(
                "tinyllama-existing",
                model="tinyllama",
                engine=LLMEngine.OLLAMA,
                status=active_status,
            )
        ]
    )

    with pytest.raises(
        DuplicateActiveDeploymentError,
        match=(
            "Model 'tinyllama' already has an "
            "active ollama deployment."
        ),
    ):
        service.deploy(
            model="tinyllama",
            engine=LLMEngine.OLLAMA,
        )


def test_different_active_ollama_model_is_allowed() -> None:
    """Different Ollama models may both be tracked."""

    service = service_with(
        [
            deployment(
                "tinyllama-existing",
                model="tinyllama",
                engine=LLMEngine.OLLAMA,
                status=ModelDeploymentStatus.RUNNING,
            )
        ]
    )

    created, _job = service.deploy(
        model="qwen2.5:1.5b",
        engine=LLMEngine.OLLAMA,
    )

    assert (
        created.model
        == "qwen2.5:1.5b"
    )
    assert (
        created.engine
        is LLMEngine.OLLAMA
    )
    assert (
        created.status
        is ModelDeploymentStatus.DEPLOYING
    )


def test_stopped_duplicate_ollama_model_is_allowed() -> None:
    """A stopped Ollama record does not block redeployment."""

    service = service_with(
        [
            deployment(
                "tinyllama-stopped",
                model="tinyllama",
                engine=LLMEngine.OLLAMA,
                status=ModelDeploymentStatus.STOPPED,
            )
        ]
    )

    created, _job = service.deploy(
        model="tinyllama",
        engine=LLMEngine.OLLAMA,
    )

    assert created.model == "tinyllama"
    assert (
        created.status
        is ModelDeploymentStatus.DEPLOYING
    )


def test_start_rejects_duplicate_active_ollama_model() -> None:
    """A stopped duplicate cannot start beside an active copy."""

    service = service_with(
        [
            deployment(
                "tinyllama-active",
                model="tinyllama",
                engine=LLMEngine.OLLAMA,
                status=ModelDeploymentStatus.RUNNING,
            ),
            deployment(
                "tinyllama-stopped",
                model="tinyllama",
                engine=LLMEngine.OLLAMA,
                status=ModelDeploymentStatus.STOPPED,
            ),
        ]
    )

    with pytest.raises(
        DuplicateActiveDeploymentError,
        match=(
            "Model 'tinyllama' already has an "
            "active ollama deployment."
        ),
    ):
        service.start(
            "tinyllama-stopped"
        )


def test_restart_rejects_duplicate_active_ollama_model() -> None:
    """Restart is blocked if another copy is active."""

    service = service_with(
        [
            deployment(
                "tinyllama-active",
                model="tinyllama",
                engine=LLMEngine.OLLAMA,
                status=ModelDeploymentStatus.RUNNING,
            ),
            deployment(
                "tinyllama-stopped",
                model="tinyllama",
                engine=LLMEngine.OLLAMA,
                status=ModelDeploymentStatus.STOPPED,
            ),
        ]
    )

    with pytest.raises(
        DuplicateActiveDeploymentError,
        match=(
            "Model 'tinyllama' already has an "
            "active ollama deployment."
        ),
    ):
        service.restart(
            "tinyllama-stopped"
        )