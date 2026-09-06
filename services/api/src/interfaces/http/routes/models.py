"""HTTP routes for model management."""

import re
from dataclasses import replace
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from application.services.model_catalog import (
    DuplicateModelError,
    ModelCatalog,
    ModelNotFoundError,
)
from domain.models.deployment import ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry
from infrastructure.config import get_settings
from infrastructure.persistence.factory import (
    get_persistent_deployment_repository,
    get_persistent_model_catalog_repository,
)
from interfaces.http.dependencies.auth import EngineerUserDependency
from interfaces.http.schemas.models import (
    ModelCreateRequest,
    ModelResponse,
    ModelUpdateRequest,
)

router = APIRouter(prefix="/models", tags=["models"])

_catalog = ModelCatalog(repository=get_persistent_model_catalog_repository())


def get_model_catalog() -> ModelCatalog:
    """Return the configured model catalog service."""

    return _catalog


ModelCatalogDependency = Annotated[ModelCatalog, Depends(get_model_catalog)]


def _runtime_available(model: ModelCatalogEntry) -> bool:
    settings = get_settings()
    timeout = 2.0
    runtime_ids = {model.model_id, model.engine_model_id, model.benchmark_model_id}

    try:
        if any(
            deployment.model in runtime_ids
            and deployment.status is ModelDeploymentStatus.RUNNING
            for deployment in get_persistent_deployment_repository().list()
        ):
            return True
    except Exception:
        pass

    try:
        if model.engine is LLMEngine.OLLAMA:
            response = httpx.get(
                f"{settings.ollama_base_url.rstrip('/')}/api/tags",
                timeout=timeout,
            )
            response.raise_for_status()
            body = response.json()
            names = {
                item.get("name")
                for item in body.get("models", [])
                if isinstance(item, dict)
            }
            return model.engine_model_id in names

        response = httpx.get(
            f"{settings.vllm_base_url.rstrip('/')}/v1/models",
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        served_models = {
            item.get("id")
            for item in body.get("data", [])
            if isinstance(item, dict)
        }
        return model.benchmark_model_id in served_models
    except Exception:
        return False


def _model_response(model: ModelCatalogEntry) -> ModelResponse:
    return ModelResponse(
        model_id=model.model_id,
        display_name=model.display_name,
        engine=model.engine,
        engine_model_id=model.engine_model_id,
        context_length=model.context_length,
        enabled=model.enabled,
        served_model_name=model.served_model_name,
        gpu_required=model.gpu_required,
        runtime_available=_runtime_available(model),
        benchmark_model_id=model.benchmark_model_id,
    )


@router.get("", response_model=list[ModelResponse])
def list_models(catalog: ModelCatalogDependency) -> list[ModelResponse]:
    """Return all models available in the platform catalog."""

    return [_model_response(model) for model in catalog.list_models()]


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{model_id}", response_model=ModelResponse)
def get_model(
    model_id: str,
    catalog: ModelCatalogDependency,
) -> ModelResponse:
    """Return one model catalog entry."""

    try:
        return _model_response(catalog.get(model_id))
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


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
        _ensure_no_runtime_duplicate(candidate, catalog, ignore_model_id=model_id)
        updated = catalog.update(model_id, **kwargs)
        return _model_response(updated)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    active_statuses = {
        ModelDeploymentStatus.DEPLOYING,
        ModelDeploymentStatus.LOADING,
        ModelDeploymentStatus.RUNNING,
    }
    runtime_ids = {model.model_id, model.engine_model_id, model.benchmark_model_id}

    for deployment in get_persistent_deployment_repository().list():
        if deployment.model in runtime_ids and deployment.status in active_statuses:
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
