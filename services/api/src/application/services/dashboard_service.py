"""Dashboard service."""

from application.ports.resource_monitor import ResourceMonitor


class DashboardService:
    """Service used to expose dashboard data."""

    def __init__(
        self,
        resource_monitor: ResourceMonitor,
        *,
        grafana_url: str = "http://127.0.0.1:3000",
        grafana_reachable: bool = False,
        prometheus_configured: bool = False,
    ) -> None:
        self._resource_monitor = resource_monitor
        self._grafana_url = grafana_url
        self._grafana_reachable = grafana_reachable
        self._prometheus_configured = prometheus_configured

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
            "pods": [
                {
                    "namespace": pod.namespace,
                    "name": pod.name,
                    "ready": pod.ready,
                }
                for pod in getattr(self._resource_monitor, "get_pod_statuses", lambda: ())()
            ],
            "alerts": [
                {
                    "name": alert.name,
                    "severity": alert.severity,
                    "state": alert.state,
                }
                for alert in getattr(self._resource_monitor, "get_alerts", lambda: ())()
            ],
            "observability": {
                "grafana_url": self._grafana_url,
                "grafana_reachable": self._grafana_reachable,
                "grafana_message": (
                    "Grafana is reachable."
                    if self._grafana_reachable
                    else "Grafana is not reachable at the configured URL."
                ),
                "prometheus_configured": self._prometheus_configured,
            },
        }
