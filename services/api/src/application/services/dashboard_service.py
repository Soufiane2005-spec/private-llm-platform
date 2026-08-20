"""Dashboard service."""

from application.ports.resource_monitor import ResourceMonitor


class DashboardService:
    """Service used to expose dashboard data."""

    def __init__(self, resource_monitor: ResourceMonitor) -> None:
        self._resource_monitor = resource_monitor

    def get_dashboard(self) -> dict:
        """Return dashboard information."""

        usage = self._resource_monitor.get_system_usage()
        engines = self._resource_monitor.get_engine_statuses()

        return {
            "resources": {
                "cpu_percent": usage.cpu_percent,
                "memory_percent": usage.memory_percent,
                "gpu_percent": usage.gpu_percent,
            },
            "engines": [
                {
                    "engine": engine.engine.value,
                    "status": engine.state.value,
                }
                for engine in engines
            ],
        }