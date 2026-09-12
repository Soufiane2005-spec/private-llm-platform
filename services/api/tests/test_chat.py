"""HTTP tests for private RAG chatbot endpoints."""

from fastapi.testclient import TestClient

from application.ports.knowledge_retriever import KnowledgeMatch
from application.services.knowledge_ingestion_service import (
    IngestedKnowledgeDocument,
)
from application.services.rag_chat_service import RagChatResult
from domain.auth.user import AuthUser, UserRole
from infrastructure.llm.ollama_chat_model import OllamaChatError
from interfaces.http.app import create_app
from interfaces.http.dependencies.auth import get_current_user
from interfaces.http.routes import chat as chat_routes

app = create_app()
client = TestClient(app)


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
            sources=[
                KnowledgeMatch(
                    source="demo_faq.md",
                    content="Contenu source",
                    score=1.0,
                    chunk_index=1,
                    page=None,
                )
            ],
            model="qwen2.5:1.5b",
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


class FakeIngestionService:
    """Fake local knowledge ingestion service."""

    def ingest_text(
        self,
        *,
        source: str,
        content: str,
    ) -> IngestedKnowledgeDocument:
        assert source == "procedure.txt"
        assert "irrigation" in content

        return IngestedKnowledgeDocument(
            source=source,
            bytes_written=len(content),
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
        "sources": [
            {
                "source": "demo_faq.md",
                "content": "Contenu source",
                "score": 1.0,
                "chunk_index": 1,
                "page": None,
            }
        ],
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


def test_ingest_knowledge_requires_authentication(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        chat_routes,
        "_ingestion_service",
        FakeIngestionService(),
    )

    response = client.post(
        "/chat/ingest",
        json={
            "source": "procedure.txt",
            "content": "Procedure irrigation sourcee.",
        },
    )

    assert response.status_code == 401


def test_engineer_can_ingest_knowledge(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        chat_routes,
        "_ingestion_service",
        FakeIngestionService(),
    )

    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        username="engineer",
        role=UserRole.ENGINEER,
    )

    try:
        response = client.post(
            "/chat/ingest",
            json={
                "source": "procedure.txt",
                "content": "Procedure irrigation sourcee.",
            },
        )
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )

    assert response.status_code == 201
    assert response.json() == {
        "source": "procedure.txt",
        "bytes_written": 29,
    }