from fastapi.testclient import TestClient

from interfaces.http.app import app

client = TestClient(app)


def test_liveness_endpoint() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_cors_allows_vite_fallback_dev_port() -> None:
    response = client.options(
        "/jobs",
        headers={
            "Origin": "http://localhost:5175",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:5175"
    )
