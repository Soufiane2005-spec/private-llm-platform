"""HTTP routes for the private RAG chatbot."""

from fastapi import APIRouter, HTTPException, status

from application.services.knowledge_ingestion_service import KnowledgeIngestionService
from application.services.model_catalog import ModelCatalog
from application.services.model_runtime_availability import ModelRuntimeAvailability
from application.services.rag_chat_service import RagChatService
from infrastructure.config import get_settings
from infrastructure.llm.ollama_chat_model import (
    OllamaChatError,
    OllamaChatModel,
)
from infrastructure.persistence.factory import get_persistent_model_catalog_repository
from infrastructure.rag.local_knowledge_retriever import (
    DEFAULT_KNOWLEDGE_DIRECTORY,
    LocalKnowledgeRetriever,
)
from interfaces.http.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSourceResponse,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
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
        model_catalog=ModelCatalog(
            repository=get_persistent_model_catalog_repository()
        ),
        runtime_availability=ModelRuntimeAvailability(
            ollama_base_url=settings.ollama_base_url,
            vllm_base_url=settings.vllm_base_url,
            timeout_seconds=2.0,
        ),
    )


_chat_service = _build_chat_service()
_ingestion_service = KnowledgeIngestionService(DEFAULT_KNOWLEDGE_DIRECTORY)


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
        model=result.model,
        reply=result.reply,
        sources=[
            ChatSourceResponse(
                source=source.source,
                content=source.content,
                score=source.score,
                chunk_index=source.chunk_index,
                page=source.page,
            )
            for source in result.sources
        ],
    )


@router.post(
    "/ingest",
    response_model=KnowledgeIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_knowledge(request: KnowledgeIngestRequest) -> KnowledgeIngestResponse:
    """Explicitly add a text document to the local RAG knowledge base."""

    try:
        result = _ingestion_service.ingest_text(
            source=request.source,
            content=request.content,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return KnowledgeIngestResponse(
        source=result.source,
        bytes_written=result.bytes_written,
    )
