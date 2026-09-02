"""Tests for the system resource monitoring provider."""

from types import SimpleNamespace

from domain.models.llm_engine import LLMEngine
from domain.models.resources import EngineRuntimeState
from infrastructure.monitoring.resource_provider import (
    SystemResourceProvider,
)


def test_get_system_usage_returns_cpu_and_memory_metrics(
    monkeypatch,
) -> None:
    """System metrics should be mapped to the domain model."""

    monkeypatch.setattr(
        "infrastructure.monitoring.resource_provider.psutil.cpu_percent",
        lambda: 37.5,
    )

    monkeypatch.setattr(
        "infrastructure.monitoring.resource_provider.psutil.virtual_memory",
        lambda: SimpleNamespace(
            percent=62.5,
            used=8_000_000_000,
            total=16_000_000_000,
        ),
    )

    provider = SystemResourceProvider()

    usage = provider.get_system_usage()

    assert usage.cpu_percent == 37.5
    assert usage.memory_percent == 62.5
    assert usage.memory_used_bytes == 8_000_000_000
    assert usage.memory_total_bytes == 16_000_000_000

    assert usage.gpu_percent is None
    assert usage.gpu_memory_used_bytes is None
    assert usage.gpu_memory_total_bytes is None


def test_get_system_usage_supports_zero_utilization(
    monkeypatch,
) -> None:
    """Zero CPU and memory usage should remain valid metrics."""

    monkeypatch.setattr(
        "infrastructure.monitoring.resource_provider.psutil.cpu_percent",
        lambda: 0.0,
    )

    monkeypatch.setattr(
        "infrastructure.monitoring.resource_provider.psutil.virtual_memory",
        lambda: SimpleNamespace(
            percent=0.0,
            used=0,
            total=16_000_000_000,
        ),
    )

    provider = SystemResourceProvider()

    usage = provider.get_system_usage()

    assert usage.cpu_percent == 0.0
    assert usage.memory_percent == 0.0
    assert usage.memory_used_bytes == 0
    assert usage.memory_total_bytes == 16_000_000_000


def test_get_engine_statuses_returns_supported_engines() -> None:
    """Monitoring should expose both configured LLM engines."""

    provider = SystemResourceProvider()

    statuses = provider.get_engine_statuses()

    assert len(statuses) == 2

    assert statuses[0].engine is LLMEngine.OLLAMA
    assert statuses[0].state is EngineRuntimeState.UNKNOWN

    assert statuses[1].engine is LLMEngine.VLLM
    assert statuses[1].state is EngineRuntimeState.UNKNOWN


def test_get_engine_statuses_returns_immutable_collection() -> None:
    """Engine status collection should use the monitor port contract."""

    provider = SystemResourceProvider()

    statuses = provider.get_engine_statuses()

    assert isinstance(statuses, tuple)