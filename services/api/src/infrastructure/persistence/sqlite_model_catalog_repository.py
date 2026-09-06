"""SQLite-backed model catalog repository."""

import sqlite3
from contextlib import closing
from pathlib import Path

from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry


class SQLiteModelCatalogRepository:
    """Persist model catalog entries in SQLite."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save(self, model: ModelCatalogEntry) -> None:
        """Store or replace a model catalog entry."""

        with closing(self._connect()) as connection:
            connection.execute(
                """
                insert into model_catalog (
                    model_id, display_name, engine, engine_model_id,
                    context_length, enabled, served_model_name, gpu_required
                )
                values (?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(model_id) do update set
                    display_name = excluded.display_name,
                    engine = excluded.engine,
                    engine_model_id = excluded.engine_model_id,
                    context_length = excluded.context_length,
                    enabled = excluded.enabled,
                    served_model_name = excluded.served_model_name,
                    gpu_required = excluded.gpu_required
                """,
                (
                    model.model_id,
                    model.display_name,
                    model.engine.value,
                    model.engine_model_id,
                    model.context_length,
                    int(model.enabled),
                    model.served_model_name,
                    int(model.gpu_required),
                ),
            )
            connection.commit()

    def get(self, model_id: str) -> ModelCatalogEntry | None:
        """Return one model by platform identifier."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                select model_id, display_name, engine, engine_model_id,
                    context_length, enabled, served_model_name, gpu_required
                from model_catalog
                where model_id = ?
                """,
                (model_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_model(row)

    def list(self) -> tuple[ModelCatalogEntry, ...]:
        """Return all models ordered by identifier."""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                select model_id, display_name, engine, engine_model_id,
                    context_length, enabled, served_model_name, gpu_required
                from model_catalog
                order by model_id
                """
            ).fetchall()

        return tuple(self._row_to_model(row) for row in rows)

    def delete(self, model_id: str) -> None:
        """Delete one model if it exists."""

        with closing(self._connect()) as connection:
            connection.execute("delete from model_catalog where model_id = ?", (model_id,))
            connection.commit()

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                create table if not exists model_catalog (
                    model_id text primary key,
                    display_name text not null,
                    engine text not null,
                    engine_model_id text not null,
                    context_length integer,
                    enabled integer not null,
                    served_model_name text,
                    gpu_required integer not null default 0
                )
                """
            )
            self._ensure_column(connection, "served_model_name", "text")
            self._ensure_column(connection, "gpu_required", "integer not null default 0")
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        column_name: str,
        column_definition: str,
    ) -> None:
        columns = {
            row["name"]
            for row in connection.execute("pragma table_info(model_catalog)").fetchall()
        }
        if column_name not in columns:
            connection.execute(
                f"alter table model_catalog add column {column_name} {column_definition}"
            )

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> ModelCatalogEntry:
        return ModelCatalogEntry(
            model_id=row["model_id"],
            display_name=row["display_name"],
            engine=LLMEngine(row["engine"]),
            engine_model_id=row["engine_model_id"],
            context_length=row["context_length"],
            enabled=bool(row["enabled"]),
            served_model_name=row["served_model_name"],
            gpu_required=bool(row["gpu_required"]),
        )
