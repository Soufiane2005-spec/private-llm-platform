"""Application port for runtime resource monitoring."""

from typing import Protocol

from domain.models.resources import (
    EngineRuntimeStatus,
    SystemResourceUsage,
)


class ResourceMonitor(Protocol):
    """Contract for runtime resource monitoring."""

    def get_system_usage(self) -> SystemResourceUsage:
        """Return the current system resource usage."""
        ...

    def get_engine_statuses(self) -> tuple[EngineRuntimeStatus, ...]:
        """Return the current status of all configured LLM engines."""
        ...