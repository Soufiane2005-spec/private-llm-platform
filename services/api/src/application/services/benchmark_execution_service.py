"""Application service for benchmark execution and persistence."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import UTC, datetime
from uuid import uuid4

from application.ports.benchmark_executor import BenchmarkExecutor
from application.ports.benchmark_repository import BenchmarkRepository
from application.ports.job_repository import JobRepository
from application.services.job_service import JobService
from application.services.model_catalog import ModelCatalog, ModelNotFoundError
from application.services.model_runtime_availability import ModelRuntimeAvailability
from domain.benchmarks.benchmark_record import BenchmarkRecord
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics
from domain.benchmarks.result import BenchmarkResult
from domain.jobs.job import Job
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry


class BenchmarkExecutionService:
    """Run benchmark suites and persist their records."""

    def __init__(
        self,
        *,
        repository: BenchmarkRepository,
        jobs: JobService,
        job_repository: JobRepository,
        model_catalog: ModelCatalog,
        ollama_executor: BenchmarkExecutor,
        vllm_executor: BenchmarkExecutor,
        resource_sampler: object,
        runtime_availability: ModelRuntimeAvailability | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")

        self._repository = repository
        self._jobs = jobs
        self._job_repository = job_repository
        self._model_catalog = model_catalog
        self._ollama_executor = ollama_executor
        self._vllm_executor = vllm_executor
        self._resource_sampler = resource_sampler
        self._runtime_availability = runtime_availability
        self._timeout_seconds = timeout_seconds

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

        catalog_model = self._require_catalog_model(model, engine)
        self._require_runtime_available(catalog_model)
        job = self._jobs.submit(f"benchmark:{engine.value}:{catalog_model.model_id}")
        job = job.mark_running().register_attempt()
        self._job_repository.save(job)

        try:
            records = self._execute_records_with_timeout(
                catalog_model=catalog_model,
                engine=engine,
                prompts=prompts,
            )
            self._save_records(records)
        except Exception as exc:
            failed = job.mark_failed(str(exc))
            self._job_repository.save(failed)
            return (), failed

        completed = job.mark_completed()
        self._job_repository.save(completed)
        return records, completed

    def start(
        self,
        *,
        model: str,
        engine: LLMEngine,
        prompts: tuple[str, ...],
    ) -> Job:
        """Create a pending benchmark job for background execution."""

        self._validate_request(model=model, prompts=prompts)
        catalog_model = self._require_catalog_model(model, engine)
        self._require_runtime_available(catalog_model)
        return self._jobs.submit(
            f"benchmark:{engine.value}:{catalog_model.model_id}",
            enqueue=False,
        )

    def execute_job(
        self,
        *,
        job_id: str,
        model: str,
        engine: LLMEngine,
        prompts: tuple[str, ...],
    ) -> tuple[BenchmarkRecord, ...]:
        """Execute a pending benchmark job and persist its records."""

        self._validate_request(model=model, prompts=prompts)
        catalog_model = self._require_catalog_model(model, engine)
        self._require_runtime_available(catalog_model)
        job = self._job_repository.get(job_id)

        if job is None:
            raise ValueError("benchmark job was not found.")

        running = job.mark_running().register_attempt()
        self._job_repository.save(running)

        try:
            records = self._execute_records_with_timeout(
                catalog_model=catalog_model,
                engine=engine,
                prompts=prompts,
            )
            self._save_records(records)
        except Exception as exc:
            failed = running.mark_failed(str(exc))
            self._job_repository.save(failed)
            return ()

        completed = running.mark_completed()
        self._job_repository.save(completed)
        return records

    def _execute_records_with_timeout(
        self,
        *,
        catalog_model: ModelCatalogEntry,
        engine: LLMEngine,
        prompts: tuple[str, ...],
    ) -> tuple[BenchmarkRecord, ...]:
        return self._execute_with_timeout(
            lambda: self._execute_records(
                catalog_model=catalog_model,
                engine=engine,
                prompts=prompts,
            )
        )

    def _execute_records(
        self,
        *,
        catalog_model: ModelCatalogEntry,
        engine: LLMEngine,
        prompts: tuple[str, ...],
    ) -> tuple[BenchmarkRecord, ...]:
        executor = self._executor_for(engine)
        return tuple(
            self._run_prompt(
                executor=executor,
                runtime_model=catalog_model.benchmark_model_id,
                model_id=catalog_model.model_id,
                prompt=prompt,
                index=index,
                engine=engine,
            )
            for index, prompt in enumerate(prompts, start=1)
        )

    def _execute_with_timeout(
        self,
        operation: Callable[[], tuple[BenchmarkRecord, ...]],
    ) -> tuple[BenchmarkRecord, ...]:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(operation)

        try:
            return future.result(timeout=self._timeout_seconds)
        except TimeoutError as exc:
            future.cancel()
            raise TimeoutError(
                f"Benchmark execution timed out after {self._timeout_seconds} seconds."
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _save_records(self, records: tuple[BenchmarkRecord, ...]) -> None:
        for record in records:
            self._repository.save(record)

    def _executor_for(self, engine: LLMEngine) -> BenchmarkExecutor:
        if engine is LLMEngine.OLLAMA:
            return self._ollama_executor

        if engine is LLMEngine.VLLM:
            return self._vllm_executor

        raise ValueError(f"Unsupported benchmark engine: {engine.value}.")

    def _require_catalog_model(
        self,
        model_id: str,
        engine: LLMEngine,
    ) -> ModelCatalogEntry:
        try:
            model = self._model_catalog.get(model_id)
        except ModelNotFoundError as exc:
            raise ValueError(f"Model '{model_id}' was not found in the catalog.") from exc

        if model.engine is not engine:
            raise ValueError(
                f"Model '{model_id}' is configured for {model.engine.value}, "
                f"not {engine.value}."
            )

        if not model.enabled:
            raise ValueError(f"Model '{model_id}' is disabled.")

        return model

    def _require_runtime_available(self, model: ModelCatalogEntry) -> None:
        if self._runtime_availability is None:
            return

        self._runtime_availability.require_benchmark_eligible(model)

    @staticmethod
    def _validate_request(*, model: str, prompts: tuple[str, ...]) -> None:
        if not model.strip():
            raise ValueError("model cannot be empty.")

        if not prompts:
            raise ValueError("at least one prompt is required.")

    def _run_prompt(
        self,
        *,
        executor: BenchmarkExecutor,
        runtime_model: str,
        model_id: str,
        prompt: str,
        index: int,
        engine: LLMEngine,
    ) -> BenchmarkRecord:
        if not prompt.strip():
            raise ValueError("prompt cannot be empty.")

        execution = executor.execute(model=runtime_model, prompt=prompt)
        resources = self._sample_resources()

        return BenchmarkRecord(
            benchmark_id=str(uuid4()),
            model_id=model_id,
            result=BenchmarkResult(
                prompt_id=f"prompt-{index}",
                engine=engine.value,
                latency_ms=execution.total_latency_ms,
                ttft_ms=execution.ttft_ms,
                tokens_generated=execution.tokens_generated,
                duration_seconds=execution.duration_seconds,
                prompt_tokens=execution.prompt_tokens,
                prompt_eval_duration_seconds=(
                    execution.prompt_eval_duration_seconds
                ),
            ),
            resources=resources,
            prompt=prompt,
            created_at=datetime.now(UTC),
            success=True,
            error=None,
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
