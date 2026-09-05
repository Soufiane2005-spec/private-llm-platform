"""Prometheus-backed platform monitoring provider."""

from dataclasses import dataclass

import httpx

from application.ports.resource_monitor import ResourceMonitor
from domain.models.llm_engine import LLMEngine
from domain.models.resources import (
    EngineRuntimeState,
    EngineRuntimeStatus,
    SystemResourceUsage,
)


class PrometheusMonitoringError(RuntimeError):
    """Raised when Prometheus cannot provide monitoring data."""


@dataclass(frozen=True, slots=True)
class KubernetesPodStatus:
    """Pod readiness status from Prometheus kube-state-metrics."""

    namespace: str
    name: str
    ready: bool


@dataclass(frozen=True, slots=True)
class PrometheusAlert:
    """Active Prometheus alert."""

    name: str
    severity: str | None
    state: str


class PrometheusResourceProvider(ResourceMonitor):
    """Collect resource, pod, and alert state from Prometheus."""

    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url cannot be empty.")

        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def get_system_usage(self) -> SystemResourceUsage:
        """Return cluster resource usage from Prometheus."""

        cpu_percent = self._query_scalar(
            '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
        )
        memory_percent = self._query_scalar(
            """
            100 * (
                1 - (
                    sum(node_memory_MemAvailable_bytes)
                    / sum(node_memory_MemTotal_bytes)
                )
            )
            """
        )
        memory_total = self._query_scalar("sum(node_memory_MemTotal_bytes)")
        memory_available = self._query_scalar("sum(node_memory_MemAvailable_bytes)")
        memory_used = max(memory_total - memory_available, 0)

        return SystemResourceUsage(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_bytes=int(memory_used),
            memory_total_bytes=max(int(memory_total), 1),
            gpu_percent=None,
            gpu_memory_used_bytes=None,
            gpu_memory_total_bytes=None,
        )

    def get_engine_statuses(self) -> tuple[EngineRuntimeStatus, ...]:
        """Return Ollama and vLLM availability from ready pods."""

        return (
            self._engine_status(LLMEngine.OLLAMA, "ollama"),
            self._engine_status(LLMEngine.VLLM, "vllm"),
        )

    def get_pod_statuses(self) -> tuple[KubernetesPodStatus, ...]:
        """Return pod readiness status for the LLM platform namespace."""

        results = self._query_vector(
            'kube_pod_status_ready{namespace="llm-platform",condition="true"}'
        )

        return tuple(
            KubernetesPodStatus(
                namespace=result["metric"].get("namespace", ""),
                name=result["metric"].get("pod", ""),
                ready=float(result["value"][1]) == 1.0,
            )
            for result in results
            if result["metric"].get("pod")
        )

    def get_alerts(self) -> tuple[PrometheusAlert, ...]:
        """Return active alerts from Prometheus."""

        results = self._query_vector("ALERTS{alertstate=\"firing\"}")

        return tuple(
            PrometheusAlert(
                name=result["metric"].get("alertname", "unknown"),
                severity=result["metric"].get("severity"),
                state=result["metric"].get("alertstate", "firing"),
            )
            for result in results
        )

    def _engine_status(self, engine: LLMEngine, app_label: str) -> EngineRuntimeStatus:
        ready = self._query_scalar(
            "sum(kube_pod_status_ready"
            f'{{namespace="llm-platform",condition="true",pod=~"{app_label}-.+"}})'
        )
        state = (
            EngineRuntimeState.AVAILABLE
            if ready > 0
            else EngineRuntimeState.UNAVAILABLE
        )

        return EngineRuntimeStatus(engine=engine, state=state)

    def _query_scalar(self, query: str) -> float:
        results = self._query_vector(query)

        if not results:
            return 0.0

        return float(results[0]["value"][1])

    def _query_vector(self, query: str) -> list[dict]:
        try:
            response = self._client.get(
                f"{self._base_url}/api/v1/query",
                params={"query": " ".join(query.split())},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PrometheusMonitoringError(
                "Unable to query Prometheus monitoring data."
            ) from exc

        if payload.get("status") != "success":
            raise PrometheusMonitoringError("Prometheus query did not succeed.")

        data = payload.get("data", {})

        if data.get("resultType") != "vector":
            raise PrometheusMonitoringError("Prometheus returned a non-vector result.")

        return list(data.get("result", []))
