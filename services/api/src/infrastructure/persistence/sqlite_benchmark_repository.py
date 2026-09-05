"""SQLite-backed benchmark repository."""

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult


class SQLiteBenchmarkRepository:
    """Persist benchmark records in SQLite."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save(self, record: BenchmarkRecord) -> None:
        """Store or replace a benchmark record."""

        with closing(self._connect()) as connection:
            connection.execute(
                """
                insert into benchmark_records (
                    benchmark_id, model_id, prompt_id, prompt, created_at,
                    engine, latency_ms, ttft_ms, tokens_generated,
                    duration_seconds, prompt_tokens,
                    prompt_eval_duration_seconds, cpu_percent, memory_percent,
                    memory_used_bytes, gpu_percent, gpu_memory_used_bytes,
                    success, error
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(benchmark_id) do update set
                    model_id = excluded.model_id,
                    prompt_id = excluded.prompt_id,
                    prompt = excluded.prompt,
                    created_at = excluded.created_at,
                    engine = excluded.engine,
                    latency_ms = excluded.latency_ms,
                    ttft_ms = excluded.ttft_ms,
                    tokens_generated = excluded.tokens_generated,
                    duration_seconds = excluded.duration_seconds,
                    prompt_tokens = excluded.prompt_tokens,
                    prompt_eval_duration_seconds = excluded.prompt_eval_duration_seconds,
                    cpu_percent = excluded.cpu_percent,
                    memory_percent = excluded.memory_percent,
                    memory_used_bytes = excluded.memory_used_bytes,
                    gpu_percent = excluded.gpu_percent,
                    gpu_memory_used_bytes = excluded.gpu_memory_used_bytes,
                    success = excluded.success,
                    error = excluded.error
                """,
                (
                    record.benchmark_id,
                    record.model_id,
                    record.prompt_id,
                    record.prompt,
                    (
                        ""
                        if record.created_at is None
                        else record.created_at.isoformat()
                    ),
                    record.engine,
                    record.latency_ms,
                    record.result.ttft_ms,
                    record.result.tokens_generated,
                    record.result.duration_seconds,
                    record.result.prompt_tokens,
                    record.result.prompt_eval_duration_seconds,
                    record.resources.cpu_percent,
                    record.resources.memory_percent,
                    record.resources.memory_used_bytes,
                    record.resources.gpu_percent,
                    record.resources.gpu_memory_used_bytes,
                    int(record.success),
                    record.error,
                ),
            )
            connection.commit()

    def list(self) -> tuple[BenchmarkRecord, ...]:
        """Return all benchmark records ordered by identifier."""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                select benchmark_id, model_id, prompt_id, engine, latency_ms,
                    ttft_ms, tokens_generated, duration_seconds, cpu_percent,
                    memory_percent, memory_used_bytes, gpu_percent,
                    gpu_memory_used_bytes, prompt, created_at, prompt_tokens,
                    prompt_eval_duration_seconds, success, error
                from benchmark_records
                order by created_at, benchmark_id
                """
            ).fetchall()

        return tuple(self._row_to_record(row) for row in rows)

    def get(self, benchmark_id: str) -> BenchmarkRecord | None:
        """Return one benchmark record by identifier."""

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                select benchmark_id, model_id, prompt_id, engine, latency_ms,
                    ttft_ms, tokens_generated, duration_seconds, cpu_percent,
                    memory_percent, memory_used_bytes, gpu_percent,
                    gpu_memory_used_bytes, prompt, created_at, prompt_tokens,
                    prompt_eval_duration_seconds, success, error
                from benchmark_records
                where benchmark_id = ?
                """,
                (benchmark_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_record(row)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                create table if not exists benchmark_records (
                    benchmark_id text primary key,
                    model_id text not null,
                    prompt_id text not null,
                    prompt text not null default '',
                    created_at text not null default '',
                    engine text not null,
                    latency_ms real not null,
                    ttft_ms real not null default 0,
                    tokens_generated integer not null,
                    duration_seconds real not null,
                    prompt_tokens integer,
                    prompt_eval_duration_seconds real,
                    cpu_percent real not null,
                    memory_percent real not null,
                    memory_used_bytes integer not null,
                    gpu_percent real,
                    gpu_memory_used_bytes integer,
                    success integer not null default 1,
                    error text
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute(
                    "pragma table_info(benchmark_records)"
                ).fetchall()
            }

            if "ttft_ms" not in columns:
                connection.execute(
                    """
                    alter table benchmark_records
                    add column ttft_ms real not null default 0
                    """
                )

            migrations = {
                "prompt": (
                    "alter table benchmark_records "
                    "add column prompt text not null default ''"
                ),
                "created_at": (
                    "alter table benchmark_records "
                    "add column created_at text not null default ''"
                ),
                "prompt_tokens": (
                    "alter table benchmark_records "
                    "add column prompt_tokens integer"
                ),
                "prompt_eval_duration_seconds": (
                    "alter table benchmark_records "
                    "add column prompt_eval_duration_seconds real"
                ),
                "success": (
                    "alter table benchmark_records "
                    "add column success integer not null default 1"
                ),
                "error": (
                    "alter table benchmark_records add column error text"
                ),
            }

            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)

            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> BenchmarkRecord:
        return BenchmarkRecord(
            benchmark_id=row["benchmark_id"],
            model_id=row["model_id"],
            result=BenchmarkResult(
                prompt_id=row["prompt_id"],
                engine=row["engine"],
                latency_ms=row["latency_ms"],
                ttft_ms=row["ttft_ms"],
                tokens_generated=row["tokens_generated"],
                duration_seconds=row["duration_seconds"],
                prompt_tokens=row["prompt_tokens"],
                prompt_eval_duration_seconds=row["prompt_eval_duration_seconds"],
            ),
            resources=BenchmarkResourceMetrics(
                cpu_percent=row["cpu_percent"],
                memory_percent=row["memory_percent"],
                memory_used_bytes=row["memory_used_bytes"],
                gpu_percent=row["gpu_percent"],
                gpu_memory_used_bytes=row["gpu_memory_used_bytes"],
            ),
            prompt=row["prompt"],
            created_at=SQLiteBenchmarkRepository._parse_timestamp(
                row["created_at"]
            ),
            success=bool(row["success"]),
            error=row["error"],
        )

    @staticmethod
    def _parse_timestamp(value: str) -> datetime | None:
        if not value:
            return None

        return datetime.fromisoformat(value)
