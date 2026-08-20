"""HTTP tests for engine selection."""

from fastapi.testclient import TestClient

from interfaces.http.app import app

client = TestClient(app)


def test_select_vllm_for_high_throughput_with_gpu() -> None:
    response = client.post(
        "/engines/select",
        json={
            "nvidia_gpu_available": True,
            "required_capabilities": [
                "openai_compatible_api",
            ],
            "preferred_capabilities": [
                "high_throughput_serving",
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["engine"] == "vllm"
    assert body["score"] == 1
    assert body["matched_preferences"] == [
        "high_throughput_serving"
    ]


def test_select_ollama_for_local_development_without_gpu() -> None:
    response = client.post(
        "/engines/select",
        json={
            "nvidia_gpu_available": False,
            "required_capabilities": [
                "local_development",
            ],
            "preferred_capabilities": [],
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["engine"] == "ollama"
    assert body["score"] == 0
    assert body["matched_preferences"] == []


def test_reject_unknown_capability() -> None:
    response = client.post(
        "/engines/select",
        json={
            "nvidia_gpu_available": True,
            "required_capabilities": [
                "unknown_capability",
            ],
            "preferred_capabilities": [],
        },
    )

    assert response.status_code == 422