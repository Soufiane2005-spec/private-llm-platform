"""Unit tests for the private chatbot application service."""

import pytest

from application.services.chat_service import ChatService


class FakeChatModel:
    """Test implementation of the chatbot model port."""

    def __init__(self) -> None:
        self.model: str | None = None
        self.message: str | None = None

    def generate_reply(
        self,
        *,
        model: str,
        message: str,
    ) -> str:
        self.model = model
        self.message = message
        return "Generated response."


def test_chat_service_generates_reply() -> None:
    """Generate a response through the configured model."""

    chat_model = FakeChatModel()
    service = ChatService(chat_model)

    reply = service.chat(
        model="qwen2.5:1.5b",
        message="Bonjour",
    )

    assert reply == "Generated response."
    assert chat_model.model == "qwen2.5:1.5b"
    assert chat_model.message == "Bonjour"


def test_chat_service_trims_input() -> None:
    """Remove unnecessary whitespace before inference."""

    chat_model = FakeChatModel()
    service = ChatService(chat_model)

    service.chat(
        model="  qwen2.5:1.5b  ",
        message="  Bonjour  ",
    )

    assert chat_model.model == "qwen2.5:1.5b"
    assert chat_model.message == "Bonjour"


def test_chat_service_rejects_empty_model() -> None:
    """Reject an empty model identifier."""

    service = ChatService(FakeChatModel())

    with pytest.raises(
        ValueError,
        match="model cannot be empty",
    ):
        service.chat(
            model="   ",
            message="Bonjour",
        )


def test_chat_service_rejects_empty_message() -> None:
    """Reject an empty user message."""

    service = ChatService(FakeChatModel())

    with pytest.raises(
        ValueError,
        match="message cannot be empty",
    ):
        service.chat(
            model="qwen2.5:1.5b",
            message="   ",
        )