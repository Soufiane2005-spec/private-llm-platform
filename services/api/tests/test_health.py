"""HTTP tests for health checks and development CORS."""

from fastapi.testclient import TestClient

from infrastructure.config import (
    DEFAULT_CORS_ALLOWED_ORIGINS,
    get_settings,
)
from interfaces.http.app import create_app

client = TestClient(create_app())


def test_liveness_endpoint() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }


def test_readiness_endpoint() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
    }


def test_cors_allows_vite_fallback_dev_port(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        ",".join(DEFAULT_CORS_ALLOWED_ORIGINS),
    )

    get_settings.cache_clear()

    try:
        test_client = TestClient(create_app())

        response = test_client.options(
            "/jobs",
            headers={
                "Origin": "http://localhost:5175",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert (
            response.headers[
                "access-control-allow-origin"
            ]
            == "http://localhost:5175"
        )
    finally:
        get_settings.cache_clear()