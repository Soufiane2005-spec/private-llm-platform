"""HTTP tests for Prometheus-compatible metrics."""

from fastapi.testclient import TestClient

from interfaces.http.app import create_app


def test_metrics_endpoint_exposes_platform_gauges() -> None:
    client = TestClient(create_app())

    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "private_llm_platform_cpu_percent" in body
    assert "private_llm_platform_jobs_total" in body
    assert "private_llm_platform_deployments_total" in body
    assert "private_llm_platform_benchmarks_total" in body
