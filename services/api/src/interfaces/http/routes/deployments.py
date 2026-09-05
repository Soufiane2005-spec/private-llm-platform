"""HTTP routes for model deployment lifecycle management."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from application.services.job_service import JobService
from application.services.model_deployment_service import ModelDeploymentService
from domain.jobs.job import Job
from domain.models.deployment import ModelDeployment
from infrastructure.config import get_settings
from infrastructure.models.kubernetes_model_deployment_manager import (
    KubernetesModelDeploymentManager,
)
from infrastructure.models.local_model_deployment_manager import (
    LocalModelDeploymentManager,
)
from infrastructure.persistence.factory import (
    get_persistent_deployment_repository,
    get_persistent_job_repository,
)
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue
from interfaces.http.dependencies.auth import EngineerUserDependency, ViewerUserDependency
from interfaces.http.schemas.deployments import (
    DeploymentCreateRequest,
    DeploymentJobResponse,
    DeploymentOperationResponse,
    DeploymentResponse,
)

router = APIRouter(prefix="/deployments", tags=["deployments"])

_deployment_repository = get_persistent_deployment_repository()
_job_repository = get_persistent_job_repository()
_job_queue = InMemoryJobQueue()
_job_service = JobService(queue=_job_queue, repository=_job_repository)
_settings = get_settings()
_deployment_service = ModelDeploymentService(
    deployments=_deployment_repository,
    manager=(
        KubernetesModelDeploymentManager(namespace=_settings.kubernetes_namespace)
        if _settings.model_deployment_backend == "kubernetes"
        else LocalModelDeploymentManager(gpu_available=False)
    ),
    jobs=_job_service,
    job_repository=_job_repository,
    timeout_seconds=_settings.model_operation_timeout_seconds,
)


def get_deployment_service() -> ModelDeploymentService:
    """Return the model deployment service."""

    return _deployment_service


DeploymentServiceDependency = Annotated[
    ModelDeploymentService,
    Depends(get_deployment_service),
]


def _deployment_response(deployment: ModelDeployment) -> DeploymentResponse:
    return DeploymentResponse(
        deployment_id=deployment.deployment_id,
        model=deployment.model,
        engine=deployment.engine,
        status=deployment.status,
        runtime_state=deployment.runtime_state,
        error=deployment.error,
        gpu_available=deployment.gpu_available,
    )


def _job_response(job: Job) -> DeploymentJobResponse:
    return DeploymentJobResponse(
        job_id=job.job_id,
        status=job.status,
        error=job.error,
    )


def _operation_response(
    deployment: ModelDeployment | None,
    job: Job,
) -> DeploymentOperationResponse:
    return DeploymentOperationResponse(
        deployment=None if deployment is None else _deployment_response(deployment),
        job=_job_response(job),
    )


@router.get("", response_model=list[DeploymentResponse])
def list_deployments(
    _user: ViewerUserDependency,
    service: DeploymentServiceDependency,
) -> list[DeploymentResponse]:
    """Return all model deployments."""

    return [
        _deployment_response(deployment)
        for deployment in service.list_deployments()
    ]


@router.post(
    "",
    response_model=DeploymentOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def deploy_model(
    request: DeploymentCreateRequest,
    background_tasks: BackgroundTasks,
    _user: EngineerUserDependency,
    service: DeploymentServiceDependency,
) -> DeploymentOperationResponse:
    """Submit a model deployment operation."""

    try:
        deployment, job = service.deploy(
            model=request.model,
            engine=request.engine,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(
        service.execute_deploy,
        deployment.deployment_id,
        job.job_id,
    )

    return _operation_response(deployment, job)


@router.get("/{deployment_id}", response_model=DeploymentResponse)
def get_deployment(
    deployment_id: str,
    _user: ViewerUserDependency,
    service: DeploymentServiceDependency,
) -> DeploymentResponse:
    """Return one model deployment."""

    deployment = service.get_deployment(deployment_id)

    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found.")

    return _deployment_response(deployment)


@router.post("/{deployment_id}/start", response_model=DeploymentOperationResponse)
def start_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    _user: EngineerUserDependency,
    service: DeploymentServiceDependency,
) -> DeploymentOperationResponse:
    """Start a model deployment."""

    try:
        deployment, job = service.start(deployment_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Deployment not found.") from exc

    background_tasks.add_task(service.execute_start, deployment_id, job.job_id)

    return _operation_response(deployment, job)


@router.post("/{deployment_id}/stop", response_model=DeploymentOperationResponse)
def stop_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    _user: EngineerUserDependency,
    service: DeploymentServiceDependency,
) -> DeploymentOperationResponse:
    """Stop a model deployment."""

    try:
        deployment, job = service.stop(deployment_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Deployment not found.") from exc

    background_tasks.add_task(service.execute_stop, deployment_id, job.job_id)

    return _operation_response(deployment, job)


@router.post("/{deployment_id}/restart", response_model=DeploymentOperationResponse)
def restart_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    _user: EngineerUserDependency,
    service: DeploymentServiceDependency,
) -> DeploymentOperationResponse:
    """Restart a model deployment."""

    try:
        deployment, job = service.restart(deployment_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Deployment not found.") from exc

    background_tasks.add_task(service.execute_restart, deployment_id, job.job_id)

    return _operation_response(deployment, job)


@router.delete("/{deployment_id}", response_model=DeploymentOperationResponse)
def delete_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    _user: EngineerUserDependency,
    service: DeploymentServiceDependency,
) -> DeploymentOperationResponse:
    """Delete a model deployment."""

    try:
        job = service.delete(deployment_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Deployment not found.") from exc

    background_tasks.add_task(service.execute_delete, deployment_id, job.job_id)

    return _operation_response(None, job)
