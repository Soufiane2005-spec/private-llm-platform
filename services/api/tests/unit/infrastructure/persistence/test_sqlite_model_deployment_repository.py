"""Tests for SQLite model deployment persistence."""

from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine
from infrastructure.persistence.sqlite_model_deployment_repository import (
    SQLiteModelDeploymentRepository,
)


def test_sqlite_model_deployment_repository_persists_deployments(tmp_path) -> None:
    """Deployments survive repository re-creation."""

    database_path = tmp_path / "platform.db"
    repository = SQLiteModelDeploymentRepository(database_path)
    deployment = ModelDeployment(
        deployment_id="deployment-1",
        model="llama3.2:1b",
        engine=LLMEngine.OLLAMA,
        status=ModelDeploymentStatus.RUNNING,
        runtime_state="ready",
        gpu_available=False,
    )

    repository.save(deployment)

    reloaded = SQLiteModelDeploymentRepository(database_path)

    assert reloaded.get("deployment-1") == deployment


def test_sqlite_model_deployment_repository_deletes_deployment(tmp_path) -> None:
    """Deployments can be deleted."""

    repository = SQLiteModelDeploymentRepository(tmp_path / "platform.db")
    repository.save(
        ModelDeployment(
            deployment_id="deployment-1",
            model="Qwen/Qwen3-0.6B",
            engine=LLMEngine.VLLM,
            status=ModelDeploymentStatus.FAILED,
            runtime_state="gpu-unavailable",
            error="gpu unavailable",
            gpu_available=False,
        )
    )

    repository.delete("deployment-1")

    assert repository.list() == ()
