"""Benchmark-based recommendation policy for LLM engines."""

from dataclasses import dataclass

from domain.benchmarks.report import BenchmarkReport
from domain.models.llm_engine import LLMEngine


@dataclass(frozen=True, slots=True)
class EngineBenchmarkCandidate:
    """Benchmark report associated with one LLM engine."""

    engine: LLMEngine
    report: BenchmarkReport


@dataclass(frozen=True, slots=True)
class BenchmarkRecommendation:
    """Recommendation produced from benchmark results."""

    engine: LLMEngine
    score: float
    rationale: tuple[str, ...]


def recommend_engine_from_benchmarks(
    candidates: tuple[EngineBenchmarkCandidate, ...],
) -> BenchmarkRecommendation:
    """Recommend the best engine using benchmark performance."""

    if not candidates:
        raise ValueError("at least one benchmark candidate is required.")

    engines = tuple(candidate.engine for candidate in candidates)

    if len(engines) != len(set(engines)):
        raise ValueError("benchmark candidates must have unique engines.")

    scored_candidates = tuple(
        (
            candidate,
            _score(candidate.report),
        )
        for candidate in candidates
    )

    selected_candidate, selected_score = max(
        scored_candidates,
        key=lambda item: item[1],
    )

    return BenchmarkRecommendation(
        engine=selected_candidate.engine,
        score=selected_score,
        rationale=_build_rationale(selected_candidate.report),
    )


def _score(report: BenchmarkReport) -> float:
    """Calculate a benchmark optimization score."""

    latency_score = 1000.0 / (1.0 + report.average_latency_ms)

    throughput_score = report.average_throughput_tokens_per_second

    resource_penalty = (
        report.average_cpu_percent
        + report.average_memory_percent
    ) / 2.0

    if report.average_gpu_percent is not None:
        resource_penalty = (
            resource_penalty + report.average_gpu_percent
        ) / 2.0

    return latency_score + throughput_score - resource_penalty


def _build_rationale(
    report: BenchmarkReport,
) -> tuple[str, ...]:
    """Build human-readable recommendation reasons."""

    rationale = [
        f"average latency: {report.average_latency_ms:.2f} ms",
        (
            "average throughput: "
            f"{report.average_throughput_tokens_per_second:.2f} tokens/s"
        ),
        f"average CPU usage: {report.average_cpu_percent:.2f}%",
        f"average memory usage: {report.average_memory_percent:.2f}%",
    ]

    if report.average_gpu_percent is not None:
        rationale.append(
            f"average GPU usage: {report.average_gpu_percent:.2f}%"
        )

    return tuple(rationale)