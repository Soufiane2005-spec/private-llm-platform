"""Runtime resource monitoring implementation."""

import psutil

from application.ports.resource_monitor import ResourceMonitor
from domain.models.llm_engine import LLMEngine
from domain.models.resources import (
    EngineRuntimeState,
    EngineRuntimeStatus,
    SystemResourceUsage,
)


class SystemResourceProvider(ResourceMonitor):
    """Collect runtime resource information."""

    def get_system_usage(self) -> SystemResourceUsage:
        """Return current system usage."""

        memory = psutil.virtual_memory()

        return SystemResourceUsage(
            cpu_percent=psutil.cpu_percent(),
            memory_percent=memory.percent,
            memory_used_bytes=memory.used,
            memory_total_bytes=memory.total,
            gpu_percent=None,
            gpu_memory_used_bytes=None,
            gpu_memory_total_bytes=None,
        )

    def get_engine_statuses(self) -> tuple[EngineRuntimeStatus, ...]:
        """Return the runtime status of the configured engines."""

        return (
            EngineRuntimeStatus(
                engine=LLMEngine.OLLAMA,
                state=EngineRuntimeState.UNKNOWN,
            ),
            EngineRuntimeStatus(
                engine=LLMEngine.VLLM,
                state=EngineRuntimeState.UNKNOWN,
            ),
        )