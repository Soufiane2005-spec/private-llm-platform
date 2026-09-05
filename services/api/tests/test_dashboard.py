"""HTTP dashboard endpoint tests."""

from fastapi.testclient import TestClient

from interfaces.http.app import app
from interfaces.http.routes import dashboard as dashboard_route


class FakeDashboardService:
    """Deterministic dashboard service for HTTP tests."""

    def get_dashboard(self) -> dict:
        """Return deterministic monitoring data."""

        return {
            "resources": {
                "cpu_percent": 25.5,
                "memory_percent": 48.0,
                "gpu_percent": 72.0,
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


class FakeCpuOnlyDashboardService:
    """Dashboard service representing a host without GPU metrics."""

    def get_dashboard(self) -> dict:
        """Return CPU-only monitoring information."""

        return {
            "resources": {
                "cpu_percent": 12.0,
                "memory_percent": 35.0,
                "gpu_percent": None,
            },
            "engines": [
                {
                    "engine": "ollama",
                    "status": "unknown",
                },
                {
                    "engine": "vllm",
                    "status": "unknown",
                },
            ],
        }


def test_dashboard_endpoint_returns_monitoring_data(
    monkeypatch,
) -> None:
    """Dashboard endpoint should expose aggregated platform metrics."""

    monkeypatch.setattr(
        dashboard_route,
        "_dashboard_service",
        FakeDashboardService(),
    )

    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200

    assert response.json() == {
        "resources": {
            "cpu_percent": 25.5,
            "memory_percent": 48.0,
            "gpu_percent": 72.0,
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
        "pods": [],
        "alerts": [],
    }


def test_dashboard_endpoint_supports_missing_gpu(
    monkeypatch,
) -> None:
    """GPU metrics should be nullable for machines without GPU data."""

    monkeypatch.setattr(
        dashboard_route,
        "_dashboard_service",
        FakeCpuOnlyDashboardService(),
    )

    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200

    body = response.json()

    assert body["resources"]["cpu_percent"] == 12.0
    assert body["resources"]["memory_percent"] == 35.0
    assert body["resources"]["gpu_percent"] is None


def test_dashboard_endpoint_exposes_engine_states(
    monkeypatch,
) -> None:
    """Dashboard should expose runtime states for supported engines."""

    monkeypatch.setattr(
        dashboard_route,
        "_dashboard_service",
        FakeCpuOnlyDashboardService(),
    )

    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200

    assert response.json()["engines"] == [
        {
            "engine": "ollama",
            "status": "unknown",
        },
        {
            "engine": "vllm",
            "status": "unknown",
        },
    ]
