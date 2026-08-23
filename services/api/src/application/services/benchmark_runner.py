"""Application service for benchmark execution."""

from collections.abc import Callable, Iterable
from time import perf_counter
from uuid import uuid4

from application.services.benchmark_report_service import (
    BenchmarkReportService,
)
from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.prompt import BenchmarkPrompt
from domain.benchmarks.report import BenchmarkReport
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult


class BenchmarkRunner:
    """Execute benchmark prompts and build benchmark records."""

    def __init__(
        self,
        executor: Callable[[BenchmarkPrompt], int],
        resource_sampler: Callable[[], BenchmarkResourceMetrics],
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._executor = executor
        self._resource_sampler = resource_sampler
        self._clock = clock
        self._report_service = BenchmarkReportService()

    def run_prompt(
        self,
        prompt: BenchmarkPrompt,
        model_id: str,
        engine: str,
    ) -> BenchmarkRecord:
        """Execute one benchmark prompt."""

        if not model_id.strip():
            raise ValueError("model_id cannot be empty.")

        if not engine.strip():
            raise ValueError("engine cannot be empty.")

        started_at = self._clock()

        tokens_generated = self._executor(prompt)

        finished_at = self._clock()

        duration_seconds = finished_at - started_at

        if duration_seconds < 0:
            raise ValueError("benchmark duration cannot be negative.")

        if tokens_generated < 0:
            raise ValueError("executor cannot return negative token count.")

        if tokens_generated > 0 and duration_seconds <= 0:
            raise ValueError(
                "benchmark duration must be greater than zero "
                "when tokens are generated."
            )

        latency_ms = duration_seconds * 1000

        resources = self._resource_sampler()

        result = BenchmarkResult(
            prompt_id=prompt.prompt_id,
            engine=engine,
            latency_ms=latency_ms,
            tokens_generated=tokens_generated,
            duration_seconds=duration_seconds,
        )

        return BenchmarkRecord(
            benchmark_id=str(uuid4()),
            model_id=model_id,
            result=result,
            resources=resources,
        )

    def run_suite(
        self,
        prompts: Iterable[BenchmarkPrompt],
        model_id: str,
        engine: str,
    ) -> tuple[tuple[BenchmarkRecord, ...], BenchmarkReport]:
        """Execute a benchmark prompt suite and generate its report."""

        benchmark_prompts = tuple(prompts)

        if not benchmark_prompts:
            raise ValueError(
                "at least one benchmark prompt is required."
            )

        records = tuple(
            self.run_prompt(
                prompt=prompt,
                model_id=model_id,
                engine=engine,
            )
            for prompt in benchmark_prompts
        )

        report = self._report_service.generate(records)

        return records, report