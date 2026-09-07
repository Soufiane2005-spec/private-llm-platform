"""HTTP schemas for the private chatbot."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Private chatbot request."""

    message: str = Field(
        min_length=1,
        max_length=10_000,
    )
    model: str = Field(
        default="qwen2.5:1.5b",
        min_length=1,
        max_length=200,
    )


class ChatSourceResponse(BaseModel):
    """Source passage metadata returned by RAG."""

    source: str
    content: str
    score: float
    chunk_index: int | None = None
    page: int | None = None


class ChatResponse(BaseModel):
    """Private chatbot response."""

    model: str
    reply: str
    sources: list[ChatSourceResponse] = Field(default_factory=list)


class KnowledgeIngestRequest(BaseModel):
    """Request to explicitly ingest local text knowledge."""

    source: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=200_000)


class KnowledgeIngestResponse(BaseModel):
    """Summary of ingested knowledge."""

    source: str
    bytes_written: int
