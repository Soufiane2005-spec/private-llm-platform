"""Application port for resource monitoring."""

from abc import ABC, abstractmethod

from domain.models.resources import (
    EngineRuntimeStatus,
    SystemResourceUsage,
)


class ResourceMonitor(ABC):
    """Abstraction used to collect runtime resource information."""

    @abstractmethod
    def get_system_usage(self) -> SystemResourceUsage:
        """Return current system resource usage."""

    @abstractmethod
    def get_engine_statuses(self) -> tuple[EngineRuntimeStatus, ...]:
        """Return the current status of all configured engines."""