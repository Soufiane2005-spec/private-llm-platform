"""SQLite-backed benchmark repository."""

import sqlite3
from contextlib import closing
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
                    benchmark_id, model_id, prompt_id, engine, latency_ms,
                    tokens_generated, duration_seconds, cpu_percent,
                    memory_percent, memory_used_bytes, gpu_percent,
                    gpu_memory_used_bytes
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(benchmark_id) do update set
                    model_id = excluded.model_id,
                    prompt_id = excluded.prompt_id,
                    engine = excluded.engine,
                    latency_ms = excluded.latency_ms,
                    tokens_generated = excluded.tokens_generated,
                    duration_seconds = excluded.duration_seconds,
                    cpu_percent = excluded.cpu_percent,
                    memory_percent = excluded.memory_percent,
                    memory_used_bytes = excluded.memory_used_bytes,
                    gpu_percent = excluded.gpu_percent,
                    gpu_memory_used_bytes = excluded.gpu_memory_used_bytes
                """,
                (
                    record.benchmark_id,
                    record.model_id,
                    record.prompt_id,
                    record.engine,
                    record.latency_ms,
                    record.result.tokens_generated,
                    record.result.duration_seconds,
                    record.resources.cpu_percent,
                    record.resources.memory_percent,
                    record.resources.memory_used_bytes,
                    record.resources.gpu_percent,
                    record.resources.gpu_memory_used_bytes,
                ),
            )
            connection.commit()

    def list(self) -> tuple[BenchmarkRecord, ...]:
        """Return all benchmark records ordered by identifier."""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                select benchmark_id, model_id, prompt_id, engine, latency_ms,
                    tokens_generated, duration_seconds, cpu_percent,
                    memory_percent, memory_used_bytes, gpu_percent,
                    gpu_memory_used_bytes
                from benchmark_records
                order by benchmark_id
                """
            ).fetchall()

        return tuple(self._row_to_record(row) for row in rows)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                create table if not exists benchmark_records (
                    benchmark_id text primary key,
                    model_id text not null,
                    prompt_id text not null,
                    engine text not null,
                    latency_ms real not null,
                    tokens_generated integer not null,
                    duration_seconds real not null,
                    cpu_percent real not null,
                    memory_percent real not null,
                    memory_used_bytes integer not null,
                    gpu_percent real,
                    gpu_memory_used_bytes integer
                )
                """
            )
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
                tokens_generated=row["tokens_generated"],
                duration_seconds=row["duration_seconds"],
            ),
            resources=BenchmarkResourceMetrics(
                cpu_percent=row["cpu_percent"],
                memory_percent=row["memory_percent"],
                memory_used_bytes=row["memory_used_bytes"],
                gpu_percent=row["gpu_percent"],
                gpu_memory_used_bytes=row["gpu_memory_used_bytes"],
            ),
        )
