"""HTTP tests for model catalog endpoints."""

from fastapi.testclient import TestClient

from interfaces.http.app import create_app

client = TestClient(create_app())


def test_list_models_returns_default_catalog() -> None:
    """Return the models configured in the default catalog."""

    response = client.get("/models")

    assert response.status_code == 200
    assert response.json() == [
        {
            "model_id": "llama-3.2-1b",
            "display_name": "Llama 3.2 1B",
            "engine": "ollama",
            "engine_model_id": "llama3.2:1b",
            "context_length": None,
            "enabled": True,
        },
        {
            "model_id": "qwen3-0.6b",
            "display_name": "Qwen3 0.6B",
            "engine": "vllm",
            "engine_model_id": "Qwen/Qwen3-0.6B",
            "context_length": 1024,
            "enabled": True,
        },
    ]