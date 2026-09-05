"""Application service for model deployment lifecycle operations."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from uuid import uuid4

from application.ports.job_repository import JobRepository
from application.ports.model_deployment_manager import ModelDeploymentManager
from application.ports.model_deployment_repository import ModelDeploymentRepository
from application.services.job_service import JobService
from domain.jobs.job import Job
from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine


class ModelDeploymentJobTimeoutError(RuntimeError):
    """Raised when a deployment job exceeds its timeout."""


class ModelDeploymentService:
    """Coordinate model deployment persistence, jobs, and runtime changes."""

    def __init__(
        self,
        *,
        deployments: ModelDeploymentRepository,
        manager: ModelDeploymentManager,
        jobs: JobService,
        job_repository: JobRepository,
        timeout_seconds: float = 120.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")

        self._deployments = deployments
        self._manager = manager
        self._jobs = jobs
        self._job_repository = job_repository
        self._timeout_seconds = timeout_seconds

    def list_deployments(self) -> tuple[ModelDeployment, ...]:
        """Return all tracked deployments."""

        return self._deployments.list()

    def get_deployment(self, deployment_id: str) -> ModelDeployment | None:
        """Return one deployment by identifier."""

        return self._deployments.get(deployment_id)

    def deploy(self, model: str, engine: LLMEngine) -> tuple[ModelDeployment, Job]:
        """Create a deployment and submit its asynchronous deployment job."""

        deployment = ModelDeployment(
            deployment_id=str(uuid4()),
            model=model.strip(),
            engine=engine,
            status=ModelDeploymentStatus.DEPLOYING,
            runtime_state="deployment-job-submitted",
        )
        self._deployments.save(deployment)

        job = self._submit_operation_job(
            f"deploy-model:{deployment.deployment_id}",
        )
        return deployment, job

    def start(self, deployment_id: str) -> tuple[ModelDeployment, Job]:
        """Submit an asynchronous deployment start job."""

        deployment = self._require_deployment(deployment_id)
        pending = deployment.with_status(
            ModelDeploymentStatus.LOADING,
            runtime_state="start-job-submitted",
            gpu_available=deployment.gpu_available,
        )
        self._deployments.save(pending)
        job = self._submit_operation_job(
            f"start-model:{deployment_id}",
        )
        return pending, job

    def stop(self, deployment_id: str) -> tuple[ModelDeployment, Job]:
        """Submit an asynchronous deployment stop job."""

        deployment = self._require_deployment(deployment_id)
        pending = deployment.with_status(
            deployment.status,
            runtime_state="stop-job-submitted",
            gpu_available=deployment.gpu_available,
        )
        self._deployments.save(pending)
        job = self._submit_operation_job(
            f"stop-model:{deployment_id}",
        )
        return pending, job

    def restart(self, deployment_id: str) -> tuple[ModelDeployment, Job]:
        """Submit an asynchronous deployment restart job."""

        deployment = self._require_deployment(deployment_id)
        pending = deployment.with_status(
            ModelDeploymentStatus.LOADING,
            runtime_state="restart-job-submitted",
            gpu_available=deployment.gpu_available,
        )
        self._deployments.save(pending)
        job = self._submit_operation_job(
            f"restart-model:{deployment_id}",
        )
        return pending, job

    def delete(self, deployment_id: str) -> Job:
        """Submit an asynchronous deployment delete job."""

        self._require_deployment(deployment_id)
        return self._submit_operation_job(f"delete-model:{deployment_id}")

    def execute_deploy(self, deployment_id: str, job_id: str) -> Job:
        """Run a submitted deployment job."""

        deployment = self._require_deployment(deployment_id)
        return self._execute_job(
            job_id,
            lambda: self._manager.deploy(deployment),
            save_deployment=True,
        )

    def execute_start(self, deployment_id: str, job_id: str) -> Job:
        """Run a submitted deployment start job."""

        deployment = self._require_deployment(deployment_id)
        return self._execute_job(
            job_id,
            lambda: self._manager.start(deployment),
            save_deployment=True,
        )

    def execute_stop(self, deployment_id: str, job_id: str) -> Job:
        """Run a submitted deployment stop job."""

        deployment = self._require_deployment(deployment_id)
        return self._execute_job(
            job_id,
            lambda: self._manager.stop(deployment),
            save_deployment=True,
        )

    def execute_restart(self, deployment_id: str, job_id: str) -> Job:
        """Run a submitted deployment restart job."""

        deployment = self._require_deployment(deployment_id)
        return self._execute_job(
            job_id,
            lambda: self._manager.restart(deployment),
            save_deployment=True,
        )

    def execute_delete(self, deployment_id: str, job_id: str) -> Job:
        """Run a submitted deployment delete job."""

        deployment = self._require_deployment(deployment_id)

        def operation() -> None:
            self._manager.delete(deployment)
            self._deployments.delete(deployment_id)

        return self._execute_job(job_id, operation, save_deployment=False)

    def _submit_operation_job(self, job_type: str) -> Job:
        return self._jobs.submit(job_type, enqueue=False)

    def _execute_job(
        self,
        job_id: str,
        operation: Callable[[], ModelDeployment | None],
        *,
        save_deployment: bool,
    ) -> Job:
        job = self._require_job(job_id)

        while job.can_retry:
            running = job.register_attempt().mark_running()
            self._job_repository.save(running)

            try:
                updated = self._execute_with_timeout(operation)

                if save_deployment and updated is not None:
                    self._deployments.save(updated)

                    if updated.error:
                        raise RuntimeError(updated.error)

            except Exception as exc:
                if running.can_retry:
                    job = running.mark_retry_pending()
                    self._job_repository.save(job)
                    continue

                failed = running.mark_failed(str(exc))
                self._job_repository.save(failed)
                return failed

            completed = running.mark_completed()
            self._job_repository.save(completed)
            return completed

        raise RuntimeError("job has no retry attempts remaining.")

    def _require_deployment(self, deployment_id: str) -> ModelDeployment:
        deployment = self._deployments.get(deployment_id)

        if deployment is None:
            raise KeyError("Deployment not found.")

        return deployment

    def _require_job(self, job_id: str) -> Job:
        job = self._job_repository.get(job_id)

        if job is None:
            raise KeyError("Job not found.")

        return job

    def _execute_with_timeout(
        self,
        operation: Callable[[], ModelDeployment | None],
    ) -> ModelDeployment | None:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(operation)

        try:
            return future.result(timeout=self._timeout_seconds)

        except FuturesTimeoutError as exc:
            future.cancel()

            raise ModelDeploymentJobTimeoutError(
                f"model operation exceeded timeout of "
                f"{self._timeout_seconds} seconds"
            ) from exc

        finally:
            executor.shutdown(wait=False, cancel_futures=True)
