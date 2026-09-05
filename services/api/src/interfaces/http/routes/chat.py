"""HTTP routes for the private RAG chatbot."""

from fastapi import APIRouter, HTTPException, status

from application.services.rag_chat_service import RagChatService
from infrastructure.config import get_settings
from infrastructure.llm.ollama_chat_model import (
    OllamaChatError,
    OllamaChatModel,
)
from infrastructure.rag.local_knowledge_retriever import (
    LocalKnowledgeRetriever,
)
from interfaces.http.schemas.chat import (
    ChatRequest,
    ChatResponse,
)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


def _build_chat_service() -> RagChatService:
    settings = get_settings()

    return RagChatService(
        chat_model=OllamaChatModel(
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_timeout_seconds,
        ),
        knowledge_retriever=LocalKnowledgeRetriever(),
    )


_chat_service = _build_chat_service()


@router.post(
    "",
    response_model=ChatResponse,
)
def chat(request: ChatRequest) -> ChatResponse:
    """Generate a response grounded in local documentation."""

    try:
        result = _chat_service.chat(
            model=request.model,
            message=request.message,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except OllamaChatError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return ChatResponse(
        model=request.model.strip(),
        reply=result.reply,
        sources=result.sources,
    )
