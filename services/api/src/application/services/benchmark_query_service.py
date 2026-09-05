"""Application service for benchmark result queries."""

from application.ports.benchmark_repository import BenchmarkRepository
from application.services.benchmark_report_service import BenchmarkReportService
from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.report import BenchmarkReport


class BenchmarkQueryService:
    """Retrieve benchmark results and aggregated reports."""

    def __init__(
        self,
        repository: BenchmarkRepository,
    ) -> None:
        self._repository = repository
        self._report_service = BenchmarkReportService()

    def list_records(self) -> tuple[BenchmarkRecord, ...]:
        """Return all stored benchmark records."""

        return self._repository.list()

    def get_record(self, benchmark_id: str) -> BenchmarkRecord | None:
        """Return one stored benchmark record by identifier."""

        return self._repository.get(benchmark_id)

    def generate_report(self) -> BenchmarkReport | None:
        """Generate a report for stored benchmarks."""

        records = self._repository.list()

        if not records:
            return None

        return self._report_service.generate(records)
