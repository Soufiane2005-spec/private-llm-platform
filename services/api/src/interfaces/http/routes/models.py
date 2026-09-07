"""HTTP routes for model management."""

import re
from collections.abc import Iterable
from dataclasses import replace
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from application.services.model_catalog import (
    DuplicateModelError,
    ModelCatalog,
    ModelNotFoundError,
)
from application.services.model_deployment_service import ModelDeploymentService
from application.services.model_runtime_availability import ModelRuntimeAvailability
from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry
from infrastructure.config import get_settings
from infrastructure.persistence.factory import (
    get_persistent_deployment_repository,
    get_persistent_model_catalog_repository,
)
from interfaces.http.dependencies.auth import EngineerUserDependency
from interfaces.http.routes.deployments import get_deployment_service
from interfaces.http.schemas.models import (
    ModelCreateRequest,
    ModelResponse,
    ModelUpdateRequest,
)

router = APIRouter(prefix="/models", tags=["models"])

_catalog = ModelCatalog(repository=get_persistent_model_catalog_repository())
_DEPLOYMENT_STATUS_UNSET = object()


def get_model_catalog() -> ModelCatalog:
    """Return the configured model catalog service."""

    return _catalog


ModelCatalogDependency = Annotated[ModelCatalog, Depends(get_model_catalog)]
DeploymentServiceDependency = Annotated[
    ModelDeploymentService,
    Depends(get_deployment_service),
]


def _runtime_checker() -> ModelRuntimeAvailability:
    settings = get_settings()
    return ModelRuntimeAvailability(
        ollama_base_url=settings.ollama_base_url,
        vllm_base_url=settings.vllm_base_url,
        timeout_seconds=0.5,
    )


def _deployment_status(model: ModelCatalogEntry) -> str | None:
    try:
        deployments = get_deployment_service().list_deployments()
    except Exception:
        try:
            deployments = get_persistent_deployment_repository().list()
        except Exception:
            return None

    return _deployment_status_from(model, deployments)


def _deployment_status_from(
    model: ModelCatalogEntry,
    deployments: Iterable[ModelDeployment],
) -> str | None:
    runtime_ids = {
        model.model_id,
        model.engine_model_id,
        model.benchmark_model_id,
    }
    statuses: list[str] = []

    for deployment in deployments:
        if deployment.model in runtime_ids:
            statuses.append(deployment.status.value)

    for preferred in (
        ModelDeploymentStatus.RUNNING.value,
        ModelDeploymentStatus.LOADING.value,
        ModelDeploymentStatus.DEPLOYING.value,
        ModelDeploymentStatus.FAILED.value,
        ModelDeploymentStatus.STOPPED.value,
    ):
        if preferred in statuses:
            return preferred

    return None


def _model_response(
    model: ModelCatalogEntry,
    runtime_checker: ModelRuntimeAvailability | None = None,
    deployment_status: str | None | object = _DEPLOYMENT_STATUS_UNSET,
) -> ModelResponse:
    runtime_state = (runtime_checker or _runtime_checker()).state_for(model)

    return ModelResponse(
        model_id=model.model_id,
        display_name=model.display_name,
        engine=model.engine,
        engine_model_id=model.engine_model_id,
        context_length=model.context_length,
        enabled=model.enabled,
        served_model_name=model.served_model_name,
        gpu_required=model.gpu_required,
        runtime_available=runtime_state.runtime_available,
        benchmark_eligible=runtime_state.benchmark_eligible,
        deployment_status=(
            _deployment_status(model)
            if deployment_status is _DEPLOYMENT_STATUS_UNSET
            else deployment_status
        ),
        benchmark_model_id=model.benchmark_model_id,
    )


@router.get("", response_model=list[ModelResponse])
def list_models(
    catalog: ModelCatalogDependency,
    deployment_service: DeploymentServiceDependency,
) -> list[ModelResponse]:
    """Return all models available in the platform catalog."""

    runtime_checker = _runtime_checker()
    models = catalog.list_models()

    try:
        deployments = deployment_service.list_deployments()
    except Exception:
        try:
            deployments = get_persistent_deployment_repository().list()
        except Exception:
            deployment_statuses = {
                model.model_id: None
                for model in models
            }
        else:
            deployment_statuses = {
                model.model_id: _deployment_status_from(model, deployments)
                for model in models
            }
    else:
        deployment_statuses = {
            model.model_id: _deployment_status_from(model, deployments)
            for model in models
        }

    return [
        _model_response(
            model,
            runtime_checker,
            deployment_status=deployment_statuses[model.model_id],
        )
        for model in models
    ]


@router.post(
    "",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_model(
    request: ModelCreateRequest,
    _user: EngineerUserDependency,
    catalog: ModelCatalogDependency,
) -> ModelResponse:
    """Create a persisted model catalog entry without deploying it."""

    model_id = request.model_id or _default_model_id(request)
    entry = ModelCatalogEntry(
        model_id=model_id,
        display_name=request.display_name.strip(),
        engine=request.engine,
        engine_model_id=request.engine_model_id.strip(),
        context_length=request.context_length,
        enabled=request.enabled,
        served_model_name=(
            request.served_model_name.strip()
            if request.served_model_name is not None
            else None
        ),
        gpu_required=request.gpu_required or request.engine is LLMEngine.VLLM,
    )

    _ensure_no_runtime_duplicate(entry, catalog)

    try:
        return _model_response(catalog.add(entry))
    except DuplicateModelError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{model_id}", response_model=ModelResponse)
def get_model(
    model_id: str,
    catalog: ModelCatalogDependency,
) -> ModelResponse:
    """Return one model catalog entry."""

    try:
        return _model_response(catalog.get(model_id))
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("/{model_id}", response_model=ModelResponse)
def update_model(
    model_id: str,
    request: ModelUpdateRequest,
    _user: EngineerUserDependency,
    catalog: ModelCatalogDependency,
) -> ModelResponse:
    """Update a persisted model catalog entry."""

    fields = request.model_fields_set
    kwargs = {
        name: getattr(request, name)
        for name in (
            "display_name",
            "engine_model_id",
            "context_length",
            "enabled",
            "served_model_name",
            "gpu_required",
        )
        if name in fields
    }

    try:
        current = catalog.get(model_id)
        candidate = replace(current, **kwargs)
        _ensure_no_runtime_duplicate(
            candidate,
            catalog,
            ignore_model_id=model_id,
        )
        updated = catalog.update(model_id, **kwargs)
        return _model_response(updated)
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    model_id: str,
    _user: EngineerUserDependency,
    catalog: ModelCatalogDependency,
) -> None:
    """Delete a model catalog entry when it is not active in runtime."""

    try:
        model = catalog.get(model_id)
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    active_statuses = {
        ModelDeploymentStatus.DEPLOYING,
        ModelDeploymentStatus.LOADING,
        ModelDeploymentStatus.RUNNING,
    }
    runtime_ids = {
        model.model_id,
        model.engine_model_id,
        model.benchmark_model_id,
    }

    for deployment in get_persistent_deployment_repository().list():
        if (
            deployment.model in runtime_ids
            and deployment.status in active_statuses
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a model with an active deployment.",
            )

    catalog.delete(model_id)


def _default_model_id(request: ModelCreateRequest) -> str:
    source = (
        request.served_model_name
        if request.engine is LLMEngine.VLLM and request.served_model_name
        else request.engine_model_id
    )
    return _slugify(source)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    if not slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="model_id could not be generated.",
        )

    return slug[:120]


def _ensure_no_runtime_duplicate(
    entry: ModelCatalogEntry,
    catalog: ModelCatalog,
    *,
    ignore_model_id: str | None = None,
) -> None:
    for existing in catalog.list_models():
        if existing.model_id == ignore_model_id:
            continue

        if existing.engine is not entry.engine:
            continue

        if existing.engine_model_id == entry.engine_model_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A model with this engine_model_id already exists.",
            )

        if (
            entry.served_model_name
            and existing.served_model_name == entry.served_model_name
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A vLLM model with this served_model_name already exists.",
            )