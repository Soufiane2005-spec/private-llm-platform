"""Persistence adapter factory for local runtime repositories."""

from application.ports.benchmark_repository import BenchmarkRepository
from application.ports.job_repository import JobRepository
from application.ports.model_deployment_repository import ModelDeploymentRepository
from infrastructure.config import get_settings
from infrastructure.persistence.sqlite_benchmark_repository import (
    SQLiteBenchmarkRepository,
)
from infrastructure.persistence.sqlite_job_repository import SQLiteJobRepository
from infrastructure.persistence.sqlite_model_deployment_repository import (
    SQLiteModelDeploymentRepository,
)

_job_repository: JobRepository | None = None
_benchmark_repository: BenchmarkRepository | None = None
_deployment_repository: ModelDeploymentRepository | None = None


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
