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


class ChatResponse(BaseModel):
    """Private chatbot response."""

    model: str
    reply: str
    sources: list[str] = Field(default_factory=list)