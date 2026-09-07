"""Tests for engine-specific deployment manager routing."""

from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine
from infrastructure.models.routed_model_deployment_manager import (
    RoutedModelDeploymentManager,
)


class RecordingManager:
    """Tiny deployment manager double that records calls."""

    def __init__(self, runtime_state: str) -> None:
        self.runtime_state = runtime_state
        self.calls: list[tuple[str, str]] = []

    def deploy(self, deployment: ModelDeployment) -> ModelDeployment:
        self.calls.append(("deploy", deployment.model))
        return deployment.with_status(
            ModelDeploymentStatus.RUNNING,
            runtime_state=self.runtime_state,
        )

    def start(self, deployment: ModelDeployment) -> ModelDeployment:
        self.calls.append(("start", deployment.model))
        return deployment.with_status(
            ModelDeploymentStatus.RUNNING,
            runtime_state=self.runtime_state,
        )

    def stop(self, deployment: ModelDeployment) -> ModelDeployment:
        self.calls.append(("stop", deployment.model))
        return deployment.with_status(
            ModelDeploymentStatus.STOPPED,
            runtime_state=self.runtime_state,
        )

    def restart(self, deployment: ModelDeployment) -> ModelDeployment:
        self.calls.append(("restart", deployment.model))
        return deployment.with_status(
            ModelDeploymentStatus.RUNNING,
            runtime_state=self.runtime_state,
        )

    def delete(self, deployment: ModelDeployment) -> None:
        self.calls.append(("delete", deployment.model))

    def status(self, deployment: ModelDeployment) -> ModelDeployment:
        self.calls.append(("status", deployment.model))
        return deployment.with_status(
            ModelDeploymentStatus.RUNNING,
            runtime_state=self.runtime_state,
        )


def _deployment(model: str, engine: LLMEngine) -> ModelDeployment:
    return ModelDeployment(
        deployment_id=f"dep-{engine.value}",
        model=model,
        engine=engine,
    )


def test_routes_ollama_deployments_to_ollama_manager() -> None:
    """Ollama deployments use the Ollama manager even in hybrid setups."""

    ollama = RecordingManager("ollama-manager")
    vllm = RecordingManager("vllm-manager")
    manager = RoutedModelDeploymentManager(
        ollama_manager=ollama,
        vllm_manager=vllm,
    )

    result = manager.deploy(_deployment("phi3-mini", LLMEngine.OLLAMA))

    assert result.runtime_state == "ollama-manager"
    assert ollama.calls == [("deploy", "phi3-mini")]
    assert vllm.calls == []


def test_routes_vllm_deployments_to_vllm_manager() -> None:
    """vLLM deployments still use the configured vLLM manager."""

    ollama = RecordingManager("ollama-manager")
    vllm = RecordingManager("vllm-manager")
    manager = RoutedModelDeploymentManager(
        ollama_manager=ollama,
        vllm_manager=vllm,
    )

    result = manager.deploy(_deployment("smollm2-135m", LLMEngine.VLLM))

    assert result.runtime_state == "vllm-manager"
    assert ollama.calls == []
    assert vllm.calls == [("deploy", "smollm2-135m")]
