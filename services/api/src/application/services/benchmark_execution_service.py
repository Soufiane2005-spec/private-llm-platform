"""Application service for benchmark execution and persistence."""

from uuid import uuid4

from application.ports.benchmark_executor import BenchmarkExecutor
from application.ports.benchmark_repository import BenchmarkRepository
from application.ports.job_repository import JobRepository
from application.services.job_service import JobService
from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult
from domain.jobs.job import Job
from domain.models.llm_engine import LLMEngine


class BenchmarkExecutionService:
    """Run benchmark suites and persist their records."""

    def __init__(
        self,
        *,
        repository: BenchmarkRepository,
        jobs: JobService,
        job_repository: JobRepository,
        ollama_executor: BenchmarkExecutor,
        resource_sampler: object,
    ) -> None:
        self._repository = repository
        self._jobs = jobs
        self._job_repository = job_repository
        self._ollama_executor = ollama_executor
        self._resource_sampler = resource_sampler

    def run(
        self,
        *,
        model: str,
        engine: LLMEngine,
        prompts: tuple[str, ...],
    ) -> tuple[tuple[BenchmarkRecord, ...], Job]:
        """Run a benchmark suite and persist each result."""

        if not model.strip():
            raise ValueError("model cannot be empty.")

        if not prompts:
            raise ValueError("at least one prompt is required.")

        job = self._jobs.submit(f"benchmark:{engine.value}:{model}")
        job = job.mark_running().register_attempt()
        self._job_repository.save(job)

        try:
            executor = self._executor_for(engine)
            records = tuple(
                self._run_prompt(
                    executor=executor,
                    model=model,
                    prompt=prompt,
                    index=index,
                    engine=engine,
                )
                for index, prompt in enumerate(prompts, start=1)
            )
        except Exception as exc:
            failed = job.mark_failed(str(exc))
            self._job_repository.save(failed)
            return (), failed

        for record in records:
            self._repository.save(record)

        completed = job.mark_completed()
        self._job_repository.save(completed)
        return records, completed

    def _executor_for(self, engine: LLMEngine) -> BenchmarkExecutor:
        if engine is LLMEngine.OLLAMA:
            return self._ollama_executor

        raise ValueError("vLLM benchmark execution requires a configured GPU runtime.")

    def _run_prompt(
        self,
        *,
        executor: BenchmarkExecutor,
        model: str,
        prompt: str,
        index: int,
        engine: LLMEngine,
    ) -> BenchmarkRecord:
        if not prompt.strip():
            raise ValueError("prompt cannot be empty.")

        execution = executor.execute(model=model, prompt=prompt)
        resources = self._sample_resources()

        return BenchmarkRecord(
            benchmark_id=str(uuid4()),
            model_id=model,
            result=BenchmarkResult(
                prompt_id=f"prompt-{index}",
                engine=engine.value,
                latency_ms=execution.total_latency_ms,
                ttft_ms=execution.ttft_ms,
                tokens_generated=execution.tokens_generated,
                duration_seconds=execution.duration_seconds,
            ),
            resources=resources,
        )

    def _sample_resources(self) -> BenchmarkResourceMetrics:
        usage = self._resource_sampler.get_system_usage()

        return BenchmarkResourceMetrics(
            cpu_percent=usage.cpu_percent,
            memory_percent=usage.memory_percent,
            memory_used_bytes=usage.memory_used_bytes,
            gpu_percent=usage.gpu_percent,
            gpu_memory_used_bytes=usage.gpu_memory_used_bytes,
        )
