"""Tests for model deployment domain objects."""

import pytest

from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine


def test_deployment_rejects_blank_model() -> None:
    """Reject deployments without a model name."""

    with pytest.raises(ValueError, match="model cannot be empty"):
        ModelDeployment(
            deployment_id="deployment-1",
            model=" ",
            engine=LLMEngine.OLLAMA,
        )


def test_failed_deployment_requires_error() -> None:
    """Failed deployments must include an actionable reason."""

    deployment = ModelDeployment(
        deployment_id="deployment-1",
        model="llama3.2:1b",
        engine=LLMEngine.OLLAMA,
    )

    with pytest.raises(ValueError, match="failed deployments"):
        deployment.with_status(
            ModelDeploymentStatus.FAILED,
            runtime_state="failed",
        )


def test_deployment_status_update_preserves_identity() -> None:
    """Status changes keep the deployment identity and model runtime."""

    deployment = ModelDeployment(
        deployment_id="deployment-1",
        model="llama3.2:1b",
        engine=LLMEngine.OLLAMA,
    )

    updated = deployment.with_status(
        ModelDeploymentStatus.RUNNING,
        runtime_state="local-runtime-ready",
        gpu_available=False,
    )

    assert updated.deployment_id == "deployment-1"
    assert updated.model == "llama3.2:1b"
    assert updated.status is ModelDeploymentStatus.RUNNING
    assert updated.runtime_state == "local-runtime-ready"
