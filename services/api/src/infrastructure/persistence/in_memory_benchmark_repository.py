"""In-memory benchmark repository implementation."""

from domain.benchmarks.benchmark_record import BenchmarkRecord


class InMemoryBenchmarkRepository:
    """Store benchmark records in memory by identifier."""

    def __init__(self) -> None:
        self._records: dict[str, BenchmarkRecord] = {}

    def save(self, record: BenchmarkRecord) -> None:
        """Store or replace a benchmark record."""

        self._records[record.benchmark_id] = record

    def list(self) -> tuple[BenchmarkRecord, ...]:
        """Return all benchmark records in deterministic order."""

        return tuple(
            self._records[benchmark_id]
            for benchmark_id in sorted(self._records)
        )

    def get(self, benchmark_id: str) -> BenchmarkRecord | None:
        """Return one benchmark record by identifier."""

        return self._records.get(benchmark_id)
