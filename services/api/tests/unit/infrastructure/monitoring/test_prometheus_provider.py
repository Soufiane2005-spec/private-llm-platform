"""Tests for Prometheus-backed monitoring."""

import httpx

from domain.models.resources import EngineRuntimeState
from infrastructure.monitoring.prometheus_provider import PrometheusResourceProvider


def prometheus_response(result: list[dict]) -> httpx.Response:
    """Build a Prometheus vector response."""

    return httpx.Response(
        200,
        json={
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": result,
            },
        },
    )


def scalar(value: float) -> list[dict]:
    """Build a scalar-like vector payload."""

    return [{"metric": {}, "value": [0, str(value)]}]


def create_client() -> httpx.Client:
    """Create a mock Prometheus client."""

    def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params["query"]

        if "node_cpu_seconds_total" in query:
            return prometheus_response(scalar(12.5))

        if "node_memory_MemAvailable_bytes" in query and "100 *" in query:
            return prometheus_response(scalar(40.0))

        if query == "sum(node_memory_MemTotal_bytes)":
            return prometheus_response(scalar(1000))

        if query == "sum(node_memory_MemAvailable_bytes)":
            return prometheus_response(scalar(600))

        if 'pod=~"ollama-.+"' in query:
            return prometheus_response(scalar(1))

        if 'pod=~"vllm-.+"' in query:
            return prometheus_response(scalar(0))

        if query.startswith("kube_pod_status_ready"):
            return prometheus_response(
                [
                    {
                        "metric": {
                            "namespace": "llm-platform",
                            "pod": "ollama-abc",
                        },
                        "value": [0, "1"],
                    }
                ]
            )

        if query.startswith("ALERTS"):
            return prometheus_response(
                [
                    {
                        "metric": {
                            "alertname": "OllamaDown",
                            "severity": "critical",
                            "alertstate": "firing",
                        },
                        "value": [0, "1"],
                    }
                ]
            )

        return prometheus_response([])

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_prometheus_provider_returns_cluster_resources() -> None:
    """Prometheus metrics are mapped to system usage."""

    provider = PrometheusResourceProvider(
        base_url="http://prometheus",
        client=create_client(),
    )

    usage = provider.get_system_usage()

    assert usage.cpu_percent == 12.5
    assert usage.memory_percent == 40.0
    assert usage.memory_total_bytes == 1000
    assert usage.memory_used_bytes == 400


def test_prometheus_provider_returns_engine_pods_and_alerts() -> None:
    """Prometheus exposes engine health, pod readiness, and alerts."""

    provider = PrometheusResourceProvider(
        base_url="http://prometheus",
        client=create_client(),
    )

    engines = provider.get_engine_statuses()
    pods = provider.get_pod_statuses()
    alerts = provider.get_alerts()

    assert engines[0].state is EngineRuntimeState.AVAILABLE
    assert engines[1].state is EngineRuntimeState.UNAVAILABLE
    assert pods[0].name == "ollama-abc"
    assert pods[0].ready
    assert alerts[0].name == "OllamaDown"
