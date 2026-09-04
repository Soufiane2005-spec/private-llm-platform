"""Application service for model deployment lifecycle operations."""

from collections.abc import Callable
from uuid import uuid4

from application.ports.job_repository import JobRepository
from application.ports.model_deployment_manager import ModelDeploymentManager
from application.ports.model_deployment_repository import ModelDeploymentRepository
from application.services.job_service import JobService
from domain.jobs.job import Job
from domain.models.deployment import ModelDeployment
from domain.models.llm_engine import LLMEngine


class ModelDeploymentService:
    """Coordinate model deployment persistence, jobs, and runtime changes."""

    def __init__(
        self,
        *,
        deployments: ModelDeploymentRepository,
        manager: ModelDeploymentManager,
        jobs: JobService,
        job_repository: JobRepository,
    ) -> None:
        self._deployments = deployments
        self._manager = manager
        self._jobs = jobs
        self._job_repository = job_repository

    def list_deployments(self) -> tuple[ModelDeployment, ...]:
        """Return all tracked deployments."""

        return self._deployments.list()

    def get_deployment(self, deployment_id: str) -> ModelDeployment | None:
        """Return one deployment by identifier."""

        return self._deployments.get(deployment_id)

    def deploy(self, model: str, engine: LLMEngine) -> tuple[ModelDeployment, Job]:
        """Create a deployment and run its deployment job."""

        deployment = ModelDeployment(
            deployment_id=str(uuid4()),
            model=model.strip(),
            engine=engine,
        )
        self._deployments.save(deployment)

        job = self._run_job(
            f"deploy-model:{deployment.deployment_id}",
            lambda: self._manager.deploy(deployment),
        )
        updated = self._deployments.get(deployment.deployment_id)

        if updated is None:
            raise RuntimeError("deployment disappeared during deployment.")

        return updated, job

    def start(self, deployment_id: str) -> tuple[ModelDeployment, Job]:
        """Start a deployment."""

        deployment = self._require_deployment(deployment_id)
        job = self._run_job(
            f"start-model:{deployment_id}",
            lambda: self._manager.start(deployment),
        )
        return self._require_deployment(deployment_id), job

    def stop(self, deployment_id: str) -> tuple[ModelDeployment, Job]:
        """Stop a deployment."""

        deployment = self._require_deployment(deployment_id)
        job = self._run_job(
            f"stop-model:{deployment_id}",
            lambda: self._manager.stop(deployment),
        )
        return self._require_deployment(deployment_id), job

    def restart(self, deployment_id: str) -> tuple[ModelDeployment, Job]:
        """Restart a deployment."""

        deployment = self._require_deployment(deployment_id)
        job = self._run_job(
            f"restart-model:{deployment_id}",
            lambda: self._manager.restart(deployment),
        )
        return self._require_deployment(deployment_id), job

    def delete(self, deployment_id: str) -> Job:
        """Delete a deployment and its runtime resources."""

        deployment = self._require_deployment(deployment_id)

        def operation() -> None:
            self._manager.delete(deployment)
            self._deployments.delete(deployment_id)

        return self._run_delete_job(f"delete-model:{deployment_id}", operation)

    def _run_job(
        self,
        job_type: str,
        operation: Callable[[], ModelDeployment],
    ) -> Job:
        job = self._jobs.submit(job_type).mark_running().register_attempt()
        self._job_repository.save(job)

        try:
            updated = operation()
            self._deployments.save(updated)
        except Exception as exc:
            failed = job.mark_failed(str(exc))
            self._job_repository.save(failed)
            return failed

        if updated.error:
            failed = job.mark_failed(updated.error)
            self._job_repository.save(failed)
            return failed

        completed = job.mark_completed()
        self._job_repository.save(completed)
        return completed

    def _run_delete_job(self, job_type: str, operation: Callable[[], None]) -> Job:
        job = self._jobs.submit(job_type).mark_running().register_attempt()
        self._job_repository.save(job)

        try:
            operation()
        except Exception as exc:
            failed = job.mark_failed(str(exc))
            self._job_repository.save(failed)
            return failed

        completed = job.mark_completed()
        self._job_repository.save(completed)
        return completed

    def _require_deployment(self, deployment_id: str) -> ModelDeployment:
        deployment = self._deployments.get(deployment_id)

        if deployment is None:
            raise KeyError("Deployment not found.")

        return deployment
