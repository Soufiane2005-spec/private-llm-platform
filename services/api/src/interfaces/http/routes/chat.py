"""HTTP routes for the private RAG chatbot."""

from fastapi import APIRouter, HTTPException, status

from application.services.rag_chat_service import RagChatService
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

_chat_service = RagChatService(
    chat_model=OllamaChatModel(),
    knowledge_retriever=LocalKnowledgeRetriever(),
)


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