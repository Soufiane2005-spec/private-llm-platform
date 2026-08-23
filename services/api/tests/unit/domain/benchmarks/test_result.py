"""Tests for benchmark result domain models."""

import pytest

from domain.benchmarks.result import BenchmarkResult


def test_benchmark_result_can_be_created() -> None:
    result = BenchmarkResult(
        prompt_id="prompt-1",
        engine="ollama",
        latency_ms=125.5,
    )

    assert result.prompt_id == "prompt-1"
    assert result.engine == "ollama"
    assert result.latency_ms == 125.5


def test_benchmark_result_accepts_zero_latency() -> None:
    result = BenchmarkResult(
        prompt_id="prompt-1",
        engine="vllm",
        latency_ms=0.0,
    )

    assert result.latency_ms == 0.0


@pytest.mark.parametrize(
    "prompt_id",
    [
        "",
        " ",
        "   ",
    ],
)
def test_benchmark_result_rejects_empty_prompt_id(
    prompt_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="prompt_id cannot be empty",
    ):
        BenchmarkResult(
            prompt_id=prompt_id,
            engine="ollama",
            latency_ms=100.0,
        )


@pytest.mark.parametrize(
    "engine",
    [
        "",
        " ",
        "   ",
    ],
)
def test_benchmark_result_rejects_empty_engine(
    engine: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="engine cannot be empty",
    ):
        BenchmarkResult(
            prompt_id="prompt-1",
            engine=engine,
            latency_ms=100.0,
        )


@pytest.mark.parametrize(
    "latency_ms",
    [
        -0.1,
        -1.0,
        -100.0,
    ],
)
def test_benchmark_result_rejects_negative_latency(
    latency_ms: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="latency_ms cannot be negative",
    ):
        BenchmarkResult(
            prompt_id="prompt-1",
            engine="ollama",
            latency_ms=latency_ms,
        )