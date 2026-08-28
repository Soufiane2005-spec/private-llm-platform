"""Tests for benchmark-based engine recommendation."""

import pytest

from domain.benchmarks.report import BenchmarkReport
from domain.models.llm_engine import LLMEngine
from domain.recommendations.benchmark_recommender import (
    EngineBenchmarkCandidate,
    recommend_engine_from_benchmarks,
)


def create_report(
    *,
    latency_ms: float,
    throughput: float,
    cpu_percent: float,
    memory_percent: float,
    gpu_percent: float | None = None,
) -> BenchmarkReport:
    return BenchmarkReport(
        benchmark_count=3,
        average_latency_ms=latency_ms,
        average_throughput_tokens_per_second=throughput,
        average_cpu_percent=cpu_percent,
        average_memory_percent=memory_percent,
        average_gpu_percent=gpu_percent,
    )


def test_recommender_selects_better_performing_engine() -> None:
    ollama = EngineBenchmarkCandidate(
        engine=LLMEngine.OLLAMA,
        report=create_report(
            latency_ms=500.0,
            throughput=20.0,
            cpu_percent=50.0,
            memory_percent=60.0,
        ),
    )

    vllm = EngineBenchmarkCandidate(
        engine=LLMEngine.VLLM,
        report=create_report(
            latency_ms=100.0,
            throughput=100.0,
            cpu_percent=30.0,
            memory_percent=40.0,
            gpu_percent=60.0,
        ),
    )

    recommendation = recommend_engine_from_benchmarks(
        (ollama, vllm)
    )

    assert recommendation.engine is LLMEngine.VLLM
    assert recommendation.rationale


def test_recommender_supports_single_candidate() -> None:
    candidate = EngineBenchmarkCandidate(
        engine=LLMEngine.OLLAMA,
        report=create_report(
            latency_ms=200.0,
            throughput=30.0,
            cpu_percent=30.0,
            memory_percent=40.0,
        ),
    )

    recommendation = recommend_engine_from_benchmarks(
        (candidate,)
    )

    assert recommendation.engine is LLMEngine.OLLAMA


def test_recommender_rejects_empty_candidates() -> None:
    with pytest.raises(
        ValueError,
        match="at least one benchmark candidate is required",
    ):
        recommend_engine_from_benchmarks(())


def test_recommender_rejects_duplicate_engines() -> None:
    report = create_report(
        latency_ms=200.0,
        throughput=30.0,
        cpu_percent=30.0,
        memory_percent=40.0,
    )

    candidates = (
        EngineBenchmarkCandidate(
            engine=LLMEngine.OLLAMA,
            report=report,
        ),
        EngineBenchmarkCandidate(
            engine=LLMEngine.OLLAMA,
            report=report,
        ),
    )

    with pytest.raises(
        ValueError,
        match="benchmark candidates must have unique engines",
    ):
        recommend_engine_from_benchmarks(candidates)


def test_recommendation_includes_gpu_rationale() -> None:
    candidate = EngineBenchmarkCandidate(
        engine=LLMEngine.VLLM,
        report=create_report(
            latency_ms=100.0,
            throughput=100.0,
            cpu_percent=30.0,
            memory_percent=40.0,
            gpu_percent=70.0,
        ),
    )

    recommendation = recommend_engine_from_benchmarks(
        (candidate,)
    )

    assert any(
        "GPU usage" in reason
        for reason in recommendation.rationale
    )