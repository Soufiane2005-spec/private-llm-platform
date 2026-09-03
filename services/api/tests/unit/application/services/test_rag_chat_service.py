"""Unit tests for the RAG chatbot service."""

from application.ports.knowledge_retriever import KnowledgeMatch
from application.services.rag_chat_service import (
    NO_INFORMATION_REPLY,
    RagChatService,
)


class FakeChatModel:
    def __init__(self) -> None:
        self.message: str | None = None

    def generate_reply(
        self,
        *,
        model: str,
        message: str,
    ) -> str:
        self.message = message
        return "Réponse générée."


class FakeRetriever:
    def search(
        self,
        query: str,
        *,
        limit: int = 3,
    ) -> list[KnowledgeMatch]:
        return [
            KnowledgeMatch(
                source="demo_irrigation.md",
                content="Une demande possède un numéro de suivi.",
                score=1.0,
            )
        ]


class EmptyRetriever:
    def search(
        self,
        query: str,
        *,
        limit: int = 3,
    ) -> list[KnowledgeMatch]:
        return []


def test_rag_chat_generates_grounded_response() -> None:
    model = FakeChatModel()

    service = RagChatService(
        chat_model=model,
        knowledge_retriever=FakeRetriever(),
    )

    result = service.chat(
        model="qwen2.5:1.5b",
        message="Comment suivre une demande ?",
    )

    assert result.reply == "Réponse générée."
    assert result.sources == ["demo_irrigation.md"]
    assert model.message is not None
    assert "demo_irrigation.md" in model.message
    assert "numéro de suivi" in model.message


def test_rag_chat_returns_safe_response_without_context() -> None:
    service = RagChatService(
        chat_model=FakeChatModel(),
        knowledge_retriever=EmptyRetriever(),
    )

    result = service.chat(
        model="qwen2.5:1.5b",
        message="Question inconnue xyzabc",
    )

    assert result.reply == NO_INFORMATION_REPLY
    assert result.sources == []