"""Tests for the dashboard application service."""

from application.services.dashboard_service import DashboardService
from domain.models.llm_engine import LLMEngine
from domain.models.resources import (
    EngineRuntimeState,
    EngineRuntimeStatus,
    SystemResourceUsage,
)


class FakeResourceMonitor:
    """Deterministic resource monitor used by dashboard tests."""

    def __init__(
        self,
        *,
        usage: SystemResourceUsage,
        engines: tuple[EngineRuntimeStatus, ...],
    ) -> None:
        self._usage = usage
        self._engines = engines

    def get_system_usage(self) -> SystemResourceUsage:
        """Return configured resource usage."""

        return self._usage

    def get_engine_statuses(
        self,
    ) -> tuple[EngineRuntimeStatus, ...]:
        """Return configured engine statuses."""

        return self._engines


def test_dashboard_returns_resource_metrics_and_engine_states() -> None:
    """Dashboard should aggregate resources and engine status."""

    monitor = FakeResourceMonitor(
        usage=SystemResourceUsage(
            cpu_percent=42.5,
            memory_percent=68.0,
            memory_used_bytes=10_000,
            memory_total_bytes=20_000,
            gpu_percent=75.0,
            gpu_memory_used_bytes=3_000,
            gpu_memory_total_bytes=4_000,
        ),
        engines=(
            EngineRuntimeStatus(
                engine=LLMEngine.OLLAMA,
                state=EngineRuntimeState.AVAILABLE,
            ),
            EngineRuntimeStatus(
                engine=LLMEngine.VLLM,
                state=EngineRuntimeState.UNAVAILABLE,
            ),
        ),
    )

    service = DashboardService(monitor)

    dashboard = service.get_dashboard()

    assert dashboard == {
        "resources": {
            "cpu_percent": 42.5,
            "memory_percent": 68.0,
            "gpu_percent": 75.0,
        },
        "engines": [
            {
                "engine": "ollama",
                "status": "available",
            },
            {
                "engine": "vllm",
                "status": "unavailable",
            },
        ],
    }


def test_dashboard_supports_unavailable_gpu_metrics() -> None:
    """Dashboard should support CPU-only monitoring hosts."""

    monitor = FakeResourceMonitor(
        usage=SystemResourceUsage(
            cpu_percent=10.0,
            memory_percent=20.0,
            memory_used_bytes=2_000,
            memory_total_bytes=10_000,
            gpu_percent=None,
            gpu_memory_used_bytes=None,
            gpu_memory_total_bytes=None,
        ),
        engines=(),
    )

    service = DashboardService(monitor)

    dashboard = service.get_dashboard()

    assert dashboard["resources"] == {
        "cpu_percent": 10.0,
        "memory_percent": 20.0,
        "gpu_percent": None,
    }

    assert dashboard["engines"] == []


def test_dashboard_exposes_unknown_engine_states() -> None:
    """Unknown runtime state should remain visible to clients."""

    monitor = FakeResourceMonitor(
        usage=SystemResourceUsage(
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_bytes=0,
            memory_total_bytes=1,
            gpu_percent=None,
            gpu_memory_used_bytes=None,
            gpu_memory_total_bytes=None,
        ),
        engines=(
            EngineRuntimeStatus(
                engine=LLMEngine.OLLAMA,
                state=EngineRuntimeState.UNKNOWN,
            ),
        ),
    )

    service = DashboardService(monitor)

    dashboard = service.get_dashboard()

    assert dashboard["engines"] == [
        {
            "engine": "ollama",
            "status": "unknown",
        }
    ]