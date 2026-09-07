"""Unit tests for the RAG chatbot service."""

from application.ports.knowledge_retriever import KnowledgeMatch
from application.services.rag_chat_service import (
    NO_INFORMATION_REPLY,
    RagChatService,
)


class FakeChatModel:
    def __init__(self) -> None:
        self.message: str | None = None
        self.model: str | None = None

    def generate_reply(
        self,
        *,
        model: str,
        message: str,
    ) -> str:
        self.model = model
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
                chunk_index=2,
                page=4,
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
    assert result.sources[0].source == "demo_irrigation.md"
    assert result.sources[0].chunk_index == 2
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


def test_rag_chat_resolves_catalog_model_to_ollama_runtime_id() -> None:
    from application.services.model_catalog import ModelCatalog
    from domain.models.llm_engine import LLMEngine
    from domain.models.model_catalog import ModelCatalogEntry
    from infrastructure.persistence.in_memory_model_catalog_repository import (
        InMemoryModelCatalogRepository,
    )

    class AlwaysAvailable:
        def state_for(self, model):
            return type(
                "State",
                (),
                {"runtime_available": True, "reason": None},
            )()

    repository = InMemoryModelCatalogRepository()
    repository.save(
        ModelCatalogEntry(
            model_id="qwen2.5-1.5b",
            display_name="Qwen2.5 1.5B",
            engine=LLMEngine.OLLAMA,
            engine_model_id="qwen2.5:1.5b",
        )
    )
    model = FakeChatModel()
    service = RagChatService(
        chat_model=model,
        knowledge_retriever=FakeRetriever(),
        model_catalog=ModelCatalog(repository=repository),
        runtime_availability=AlwaysAvailable(),
    )

    result = service.chat(model="qwen2.5-1.5b", message="Comment suivre une demande ?")

    assert result.model == "qwen2.5:1.5b"
    assert model.model == "qwen2.5:1.5b"


def test_rag_chat_rejects_runtime_unavailable_model() -> None:
    from application.services.model_catalog import ModelCatalog
    from domain.models.llm_engine import LLMEngine
    from domain.models.model_catalog import ModelCatalogEntry
    from infrastructure.persistence.in_memory_model_catalog_repository import (
        InMemoryModelCatalogRepository,
    )

    class Unavailable:
        def state_for(self, model):
            return type(
                "State",
                (),
                {"runtime_available": False, "reason": "not installed"},
            )()

    repository = InMemoryModelCatalogRepository()
    repository.save(
        ModelCatalogEntry(
            model_id="phi3-mini",
            display_name="Phi-3 Mini",
            engine=LLMEngine.OLLAMA,
            engine_model_id="phi3:mini",
        )
    )
    service = RagChatService(
        chat_model=FakeChatModel(),
        knowledge_retriever=FakeRetriever(),
        model_catalog=ModelCatalog(repository=repository),
        runtime_availability=Unavailable(),
    )

    import pytest

    with pytest.raises(ValueError, match="not runtime available"):
        service.chat(model="phi3-mini", message="Comment suivre une demande ?")
