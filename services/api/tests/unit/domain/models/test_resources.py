import pytest

from domain.models.llm_engine import LLMEngine
from domain.models.resources import (
    EngineRuntimeState,
    EngineRuntimeStatus,
    SystemResourceUsage,
)


def test_create_system_resource_usage() -> None:
    usage = SystemResourceUsage(
        cpu_percent=35.5,
        memory_percent=62.0,
        memory_used_bytes=8_000_000_000,
        memory_total_bytes=16_000_000_000,
        gpu_percent=70.0,
        gpu_memory_used_bytes=3_000_000_000,
        gpu_memory_total_bytes=4_000_000_000,
    )

    assert usage.cpu_percent == 35.5
    assert usage.gpu_percent == 70.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cpu_percent", -1.0),
        ("cpu_percent", 101.0),
        ("memory_percent", -1.0),
        ("memory_percent", 101.0),
        ("gpu_percent", -1.0),
        ("gpu_percent", 101.0),
    ],
)
def test_reject_invalid_percentage(
    field: str,
    value: float,
) -> None:
    values = {
        "cpu_percent": 10.0,
        "memory_percent": 20.0,
        "memory_used_bytes": 1,
        "memory_total_bytes": 2,
        "gpu_percent": 30.0,
    }
    values[field] = value

    with pytest.raises(ValueError):
        SystemResourceUsage(**values)


def test_create_engine_runtime_status() -> None:
    status = EngineRuntimeStatus(
        engine=LLMEngine.VLLM,
        state=EngineRuntimeState.AVAILABLE,
    )

    assert status.engine is LLMEngine.VLLM
    assert status.state is EngineRuntimeState.AVAILABLE