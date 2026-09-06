"""Persistence adapter factory for local runtime repositories."""

from application.ports.benchmark_repository import BenchmarkRepository
from application.ports.job_repository import JobRepository
from application.ports.model_catalog_repository import ModelCatalogRepository
from application.ports.model_deployment_repository import ModelDeploymentRepository
from application.services.default_model_catalog import default_model_catalog_entries
from infrastructure.config import get_settings
from infrastructure.persistence.sqlite_benchmark_repository import (
    SQLiteBenchmarkRepository,
)
from infrastructure.persistence.sqlite_job_repository import SQLiteJobRepository
from infrastructure.persistence.sqlite_model_catalog_repository import (
    SQLiteModelCatalogRepository,
)
from infrastructure.persistence.sqlite_model_deployment_repository import (
    SQLiteModelDeploymentRepository,
)

_job_repository: JobRepository | None = None
_benchmark_repository: BenchmarkRepository | None = None
_deployment_repository: ModelDeploymentRepository | None = None
_model_catalog_repository: ModelCatalogRepository | None = None


def get_persistent_job_repository() -> JobRepository:
    """Return the configured persistent job repository."""

    global _job_repository

    if _job_repository is None:
        _job_repository = SQLiteJobRepository(get_settings().sqlite_database_path)

    return _job_repository


def get_persistent_benchmark_repository() -> BenchmarkRepository:
    """Return the configured persistent benchmark repository."""

    global _benchmark_repository

    if _benchmark_repository is None:
        _benchmark_repository = SQLiteBenchmarkRepository(
            get_settings().sqlite_database_path
        )

    return _benchmark_repository


def get_persistent_deployment_repository() -> ModelDeploymentRepository:
    """Return the configured persistent deployment repository."""

    global _deployment_repository

    if _deployment_repository is None:
        _deployment_repository = SQLiteModelDeploymentRepository(
            get_settings().sqlite_database_path
        )

    return _deployment_repository


def get_persistent_model_catalog_repository() -> ModelCatalogRepository:
    """Return the configured persistent model catalog repository."""

    global _model_catalog_repository

    if _model_catalog_repository is None:
        repository = SQLiteModelCatalogRepository(get_settings().sqlite_database_path)

        if repository.get("qwen3-0.6b") is not None:
            repository.delete("qwen3-0.6b")

        for entry in default_model_catalog_entries():
            if repository.get(entry.model_id) is None:
                repository.save(entry)

        _model_catalog_repository = repository

    return _model_catalog_repository
