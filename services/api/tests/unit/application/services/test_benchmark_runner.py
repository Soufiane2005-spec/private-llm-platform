"""Tests for benchmark execution service."""

import pytest

from application.services.benchmark_runner import BenchmarkRunner
from domain.benchmarks.prompt import BenchmarkPrompt, PromptCategory
from domain.benchmarks.resource_metrics import BenchmarkResourceMetrics


def create_prompt(
    prompt_id: str = "prompt-1",
) -> BenchmarkPrompt:
    """Create a benchmark prompt for tests."""

    return BenchmarkPrompt(
        prompt_id=prompt_id,
        category=PromptCategory.SHORT,
        text="Explain artificial intelligence.",
    )


def create_resources() -> BenchmarkResourceMetrics:
    """Create benchmark resource metrics for tests."""

    return BenchmarkResourceMetrics(
        cpu_percent=40.0,
        memory_percent=50.0,
        memory_used_bytes=4_000_000_000,
        gpu_percent=60.0,
        gpu_memory_used_bytes=2_000_000_000,
    )


def test_runner_executes_single_prompt() -> None:
    clock_values = iter([10.0, 12.0])

    runner = BenchmarkRunner(
        executor=lambda prompt: 100,
        resource_sampler=create_resources,
        clock=lambda: next(clock_values),
    )

    record = runner.run_prompt(
        prompt=create_prompt(),
        model_id="qwen3-0.6b",
        engine="vllm",
    )

    assert record.model_id == "qwen3-0.6b"
    assert record.prompt_id == "prompt-1"
    assert record.engine == "vllm"
    assert record.latency_ms == 2000.0
    assert record.result.tokens_generated == 100
    assert record.result.duration_seconds == 2.0
    assert record.throughput_tokens_per_second == 50.0
    assert record.resources == create_resources()


def test_runner_generates_unique_benchmark_id() -> None:
    clock_values = iter([1.0, 2.0])

    runner = BenchmarkRunner(
        executor=lambda prompt: 10,
        resource_sampler=create_resources,
        clock=lambda: next(clock_values),
    )

    record = runner.run_prompt(
        prompt=create_prompt(),
        model_id="qwen3-0.6b",
        engine="ollama",
    )

    assert record.benchmark_id


def test_runner_supports_zero_generated_tokens() -> None:
    clock_values = iter([1.0, 2.0])

    runner = BenchmarkRunner(
        executor=lambda prompt: 0,
        resource_sampler=create_resources,
        clock=lambda: next(clock_values),
    )

    record = runner.run_prompt(
        prompt=create_prompt(),
        model_id="qwen3-0.6b",
        engine="ollama",
    )

    assert record.result.tokens_generated == 0
    assert record.throughput_tokens_per_second == 0.0


def test_runner_rejects_empty_model_id() -> None:
    runner = BenchmarkRunner(
        executor=lambda prompt: 10,
        resource_sampler=create_resources,
    )

    with pytest.raises(
        ValueError,
        match="model_id cannot be empty",
    ):
        runner.run_prompt(
            prompt=create_prompt(),
            model_id=" ",
            engine="ollama",
        )


def test_runner_rejects_empty_engine() -> None:
    runner = BenchmarkRunner(
        executor=lambda prompt: 10,
        resource_sampler=create_resources,
    )

    with pytest.raises(
        ValueError,
        match="engine cannot be empty",
    ):
        runner.run_prompt(
            prompt=create_prompt(),
            model_id="qwen3-0.6b",
            engine=" ",
        )


def test_runner_rejects_negative_executor_tokens() -> None:
    clock_values = iter([1.0, 2.0])

    runner = BenchmarkRunner(
        executor=lambda prompt: -1,
        resource_sampler=create_resources,
        clock=lambda: next(clock_values),
    )

    with pytest.raises(
        ValueError,
        match="executor cannot return negative token count",
    ):
        runner.run_prompt(
            prompt=create_prompt(),
            model_id="qwen3-0.6b",
            engine="ollama",
        )


def test_runner_rejects_negative_duration() -> None:
    clock_values = iter([2.0, 1.0])

    runner = BenchmarkRunner(
        executor=lambda prompt: 10,
        resource_sampler=create_resources,
        clock=lambda: next(clock_values),
    )

    with pytest.raises(
        ValueError,
        match="benchmark duration cannot be negative",
    ):
        runner.run_prompt(
            prompt=create_prompt(),
            model_id="qwen3-0.6b",
            engine="ollama",
        )


def test_runner_requires_positive_duration_when_tokens_generated() -> None:
    clock_values = iter([1.0, 1.0])

    runner = BenchmarkRunner(
        executor=lambda prompt: 10,
        resource_sampler=create_resources,
        clock=lambda: next(clock_values),
    )

    with pytest.raises(
        ValueError,
        match=(
            "benchmark duration must be greater than zero "
            "when tokens are generated"
        ),
    ):
        runner.run_prompt(
            prompt=create_prompt(),
            model_id="qwen3-0.6b",
            engine="ollama",
        )


def test_runner_executes_suite_and_generates_report() -> None:
    clock_values = iter(
        [
            0.0,
            2.0,
            10.0,
            14.0,
        ]
    )

    runner = BenchmarkRunner(
        executor=lambda prompt: 100,
        resource_sampler=create_resources,
        clock=lambda: next(clock_values),
    )

    prompts = [
        create_prompt("prompt-1"),
        create_prompt("prompt-2"),
    ]

    records, report = runner.run_suite(
        prompts=prompts,
        model_id="qwen3-0.6b",
        engine="vllm",
    )

    assert len(records) == 2

    assert records[0].latency_ms == 2000.0
    assert records[1].latency_ms == 4000.0

    assert report.benchmark_count == 2
    assert report.average_latency_ms == 3000.0
    assert report.average_throughput_tokens_per_second == 37.5

    assert report.average_cpu_percent == 40.0
    assert report.average_memory_percent == 50.0
    assert report.average_gpu_percent == 60.0


def test_runner_rejects_empty_suite() -> None:
    runner = BenchmarkRunner(
        executor=lambda prompt: 10,
        resource_sampler=create_resources,
    )

    with pytest.raises(
        ValueError,
        match="at least one benchmark prompt is required",
    ):
        runner.run_suite(
            prompts=[],
            model_id="qwen3-0.6b",
            engine="vllm",
        )