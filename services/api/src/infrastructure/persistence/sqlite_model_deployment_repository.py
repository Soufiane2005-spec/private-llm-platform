"""SQLite-backed model deployment repository."""

import sqlite3
from contextlib import closing
from pathlib import Path

from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine


class SQLiteModelDeploymentRepository:
    """Persist model deployments in SQLite."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save(self, deployment: ModelDeployment) -> None:
        """Store or replace a deployment."""

        with closing(self._connect()) as connection:
            connection.execute(
                """
                insert into model_deployments (
                    deployment_id, model, engine, status, runtime_state,
                    error, gpu_available
                )
                values (?, ?, ?, ?, ?, ?, ?)
                on conflict(deployment_id) do update set
                    model = excluded.model,
                    engine = excluded.engine,
                    status = excluded.status,
                    runtime_state = excluded.runtime_state,
                    error = excluded.error,
                    gpu_available = excluded.gpu_available
                """,
                (
                    deployment.deployment_id,
                    deployment.model,
                    deployment.engine.value,
                    deployment.status.value,
                    deployment.runtime_state,
                    deployment.error,
                    None
                    if deployment.gpu_available is None
                    else int(deployment.gpu_available),
                ),
            )
            connection.commit()

    def get(self, deployment_id: str) -> ModelDeployment | None:
        """Return one deployment by identifier."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                select deployment_id, model, engine, status, runtime_state,
                    error, gpu_available
                from model_deployments
                where deployment_id = ?
                """,
                (deployment_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_deployment(row)

    def list(self) -> tuple[ModelDeployment, ...]:
        """Return all deployments ordered by identifier."""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                select deployment_id, model, engine, status, runtime_state,
                    error, gpu_available
                from model_deployments
                order by deployment_id
                """
            ).fetchall()

        return tuple(self._row_to_deployment(row) for row in rows)

    def delete(self, deployment_id: str) -> None:
        """Delete one deployment if it exists."""

        with closing(self._connect()) as connection:
            connection.execute(
                "delete from model_deployments where deployment_id = ?",
                (deployment_id,),
            )
            connection.commit()

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                create table if not exists model_deployments (
                    deployment_id text primary key,
                    model text not null,
                    engine text not null,
                    status text not null,
                    runtime_state text not null,
                    error text,
                    gpu_available integer
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _row_to_deployment(row: sqlite3.Row) -> ModelDeployment:
        raw_gpu_available = row["gpu_available"]
        gpu_available = (
            None if raw_gpu_available is None else bool(raw_gpu_available)
        )

        return ModelDeployment(
            deployment_id=row["deployment_id"],
            model=row["model"],
            engine=LLMEngine(row["engine"]),
            status=ModelDeploymentStatus(row["status"]),
            runtime_state=row["runtime_state"],
            error=row["error"],
            gpu_available=gpu_available,
        )
