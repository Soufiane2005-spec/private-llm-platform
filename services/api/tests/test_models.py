"""HTTP tests for model catalog endpoints."""

import pytest
from fastapi.testclient import TestClient

from application.services.auth_service import AuthService
from application.services.model_catalog import ModelCatalog, ModelNotFoundError
from domain.auth.user import PlatformUser, UserRole
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry
from infrastructure.persistence.in_memory_model_catalog_repository import (
    InMemoryModelCatalogRepository,
)
from infrastructure.persistence.in_memory_user_repository import InMemoryUserRepository
from infrastructure.security.jwt_token_service import JWTTokenService
from interfaces.http.app import create_app
from interfaces.http.dependencies.auth import get_auth_service
from interfaces.http.routes.models import get_model_catalog


class TestPasswordHasher:
    """Deterministic password checker."""

    def verify(self, password: str, password_hash: str) -> bool:
        return password == "correct-password" and password_hash == "hash"

    def hash(self, password: str) -> str:
        return f"hashed:{password}"


def auth_service(role: UserRole = UserRole.ADMIN) -> AuthService:
    """Create an auth service for protected model routes."""

    return AuthService(
        user_repository=InMemoryUserRepository(
            (
                PlatformUser(
                    username="admin",
                    password_hash="hash",
                    role=role,
                ),
            )
        ),
        password_hasher=TestPasswordHasher(),
        token_service=JWTTokenService(
            secret_key="model-test-secret-long-enough-for-hs256",
            algorithm="HS256",
            expire_minutes=30,
        ),
    )


def create_test_client(role: UserRole = UserRole.ADMIN) -> tuple[TestClient, ModelCatalog]:
    """Create a client with an isolated model catalog."""

    repository = InMemoryModelCatalogRepository()
    repository.save(
        ModelCatalogEntry(
            model_id="qwen2.5-1.5b",
            display_name="Qwen2.5 1.5B",
            engine=LLMEngine.OLLAMA,
            engine_model_id="qwen2.5:1.5b",
        )
    )
    repository.save(
        ModelCatalogEntry(
            model_id="smollm2-135m",
            display_name="SmolLM2 135M",
            engine=LLMEngine.VLLM,
            engine_model_id="HuggingFaceTB/SmolLM2-135M-Instruct",
            context_length=1024,
            served_model_name="smollm2-135m",
            gpu_required=True,
        )
    )
    catalog = ModelCatalog(repository=repository)
    app = create_app()
    app.dependency_overrides[get_model_catalog] = lambda: catalog
    app.dependency_overrides[get_auth_service] = lambda: auth_service(role)
    return TestClient(app), catalog


def bearer(client: TestClient) -> dict[str, str]:
    """Return auth headers."""

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "correct-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_list_models_returns_default_catalog() -> None:
    """Return the models configured in the default catalog."""

    client, _catalog = create_test_client()
    response = client.get("/models")

    assert response.status_code == 200
    body = response.json()
    assert [model["model_id"] for model in body] == [
        "qwen2.5-1.5b",
        "smollm2-135m",
    ]
    assert body[1]["display_name"] == "SmolLM2 135M"
    assert body[1]["engine_model_id"] == "HuggingFaceTB/SmolLM2-135M-Instruct"
    assert body[1]["served_model_name"] == "smollm2-135m"
    assert body[1]["benchmark_model_id"] == "smollm2-135m"


def test_create_vllm_model_persists_catalog_entry() -> None:
    client, catalog = create_test_client()

    response = client.post(
        "/models",
        json={
            "display_name": "SmolLM2 360M",
            "engine": "vllm",
            "engine_model_id": "HuggingFaceTB/SmolLM2-360M-Instruct",
            "served_model_name": "smollm2-360m",
            "context_length": 2048,
            "enabled": True,
        },
        headers=bearer(client),
    )

    assert response.status_code == 201
    assert response.json()["model_id"] == "smollm2-360m"
    assert catalog.get("smollm2-360m").served_model_name == "smollm2-360m"


def test_create_model_rejects_duplicate_runtime_id() -> None:
    client, _catalog = create_test_client()

    response = client.post(
        "/models",
        json={
            "display_name": "Duplicate",
            "engine": "vllm",
            "engine_model_id": "HuggingFaceTB/SmolLM2-135M-Instruct",
            "served_model_name": "duplicate",
        },
        headers=bearer(client),
    )

    assert response.status_code == 409


def test_viewer_cannot_create_model() -> None:
    client, _catalog = create_test_client(UserRole.VIEWER)

    response = client.post(
        "/models",
        json={
            "display_name": "Llama",
            "engine": "ollama",
            "engine_model_id": "llama3.2:3b",
        },
        headers=bearer(client),
    )

    assert response.status_code == 403


def test_patch_model_updates_enabled_state() -> None:
    client, _catalog = create_test_client()

    response = client.patch(
        "/models/smollm2-135m",
        json={"enabled": False},
        headers=bearer(client),
    )

    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_delete_model_removes_catalog_entry() -> None:
    client, catalog = create_test_client()
    catalog.add(
        ModelCatalogEntry(
            model_id="llama3-2-3b",
            display_name="Llama 3.2 3B",
            engine=LLMEngine.OLLAMA,
            engine_model_id="llama3.2:3b",
        )
    )

    response = client.delete(
        "/models/llama3-2-3b",
        headers=bearer(client),
    )

    assert response.status_code == 204
    with pytest.raises(ModelNotFoundError):
        catalog.get("llama3-2-3b")
