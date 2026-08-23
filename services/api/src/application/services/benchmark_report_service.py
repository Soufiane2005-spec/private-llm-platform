"""Application service for benchmark report generation."""

from collections.abc import Iterable

from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.report import BenchmarkReport


class BenchmarkReportService:
    """Generate aggregate reports from benchmark records."""

    def generate(
        self,
        records: Iterable[BenchmarkRecord],
    ) -> BenchmarkReport:
        """Generate an aggregated benchmark report."""

        benchmark_records = tuple(records)

        if not benchmark_records:
            raise ValueError(
                "at least one benchmark record is required."
            )

        count = len(benchmark_records)

        average_latency_ms = (
            sum(record.latency_ms for record in benchmark_records)
            / count
        )

        average_throughput = (
            sum(
                record.throughput_tokens_per_second
                for record in benchmark_records
            )
            / count
        )

        average_cpu_percent = (
            sum(
                record.resources.cpu_percent
                for record in benchmark_records
            )
            / count
        )

        average_memory_percent = (
            sum(
                record.resources.memory_percent
                for record in benchmark_records
            )
            / count
        )

        gpu_values = [
            record.resources.gpu_percent
            for record in benchmark_records
            if record.resources.gpu_percent is not None
        ]

        average_gpu_percent = (
            sum(gpu_values) / len(gpu_values)
            if gpu_values
            else None
        )

        return BenchmarkReport(
            benchmark_count=count,
            average_latency_ms=average_latency_ms,
            average_throughput_tokens_per_second=average_throughput,
            average_cpu_percent=average_cpu_percent,
            average_memory_percent=average_memory_percent,
            average_gpu_percent=average_gpu_percent,
        )