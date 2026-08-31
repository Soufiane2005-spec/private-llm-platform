"""Application port for benchmark persistence."""

from typing import Protocol

from domain.benchmarks.benchmark_record import BenchmarkRecord


class BenchmarkRepository(Protocol):
    """Persistence contract for benchmark records."""

    def save(self, record: BenchmarkRecord) -> None:
        """Store or replace a benchmark record."""
        ...

    def list(self) -> tuple[BenchmarkRecord, ...]:
        """Return all benchmark records."""
        ...