"""HTTP tests for private RAG chatbot endpoints."""

from fastapi.testclient import TestClient

from application.services.rag_chat_service import RagChatResult
from infrastructure.llm.ollama_chat_model import OllamaChatError
from interfaces.http.app import create_app
from interfaces.http.routes import chat as chat_routes

client = TestClient(create_app())


class SuccessfulChatService:
    """Fake RAG chatbot service."""

    def chat(
        self,
        *,
        model: str,
        message: str,
    ) -> RagChatResult:
        assert model == "qwen2.5:1.5b"
        assert message == "Bonjour"

        return RagChatResult(
            reply="Réponse documentaire.",
            sources=["demo_faq.md"],
        )


class InvalidChatService:
    """Fake service raising a validation error."""

    def chat(
        self,
        *,
        model: str,
        message: str,
    ) -> RagChatResult:
        raise ValueError("message cannot be empty.")


class UnavailableChatService:
    """Fake service simulating unavailable Ollama."""

    def chat(
        self,
        *,
        model: str,
        message: str,
    ) -> RagChatResult:
        raise OllamaChatError(
            "Unable to communicate with Ollama."
        )


def test_chat_returns_rag_response(monkeypatch) -> None:
    monkeypatch.setattr(
        chat_routes,
        "_chat_service",
        SuccessfulChatService(),
    )

    response = client.post(
        "/chat",
        json={
            "message": "Bonjour",
            "model": "qwen2.5:1.5b",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "model": "qwen2.5:1.5b",
        "reply": "Réponse documentaire.",
        "sources": ["demo_faq.md"],
    }


def test_chat_rejects_empty_message() -> None:
    response = client.post(
        "/chat",
        json={
            "message": "",
            "model": "qwen2.5:1.5b",
        },
    )

    assert response.status_code == 422


def test_chat_returns_bad_request(monkeypatch) -> None:
    monkeypatch.setattr(
        chat_routes,
        "_chat_service",
        InvalidChatService(),
    )

    response = client.post(
        "/chat",
        json={
            "message": "Bonjour",
            "model": "qwen2.5:1.5b",
        },
    )

    assert response.status_code == 400


def test_chat_returns_service_unavailable(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        chat_routes,
        "_chat_service",
        UnavailableChatService(),
    )

    response = client.post(
        "/chat",
        json={
            "message": "Bonjour",
            "model": "qwen2.5:1.5b",
        },
    )

    assert response.status_code == 503