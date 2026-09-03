"""Unit tests for the Ollama chatbot adapter."""

import httpx
import pytest

from infrastructure.llm.ollama_chat_model import (
    OllamaChatError,
    OllamaChatModel,
)


class FakeResponse:
    """Minimal HTTP response used by Ollama adapter tests."""

    def __init__(
        self,
        *,
        payload: object,
        error: bool = False,
    ) -> None:
        self._payload = payload
        self._error = error

    def raise_for_status(self) -> None:
        if self._error:
            raise httpx.HTTPStatusError(
                "Ollama error",
                request=httpx.Request(
                    "POST",
                    "http://127.0.0.1:11434/api/chat",
                ),
                response=httpx.Response(500),
            )

    def json(self) -> object:
        return self._payload


def test_generate_reply_returns_ollama_response(
    monkeypatch,
) -> None:
    """Return generated text received from Ollama."""

    def fake_post(
        url: str,
        *,
        json: dict,
        timeout: float,
    ) -> FakeResponse:
        assert url == "http://127.0.0.1:11434/api/chat"
        assert timeout == 120.0
        assert json == {
            "model": "qwen2.5:1.5b",
            "messages": [
                {
                    "role": "user",
                    "content": "Bonjour",
                }
            ],
            "stream": False,
        }

        return FakeResponse(
            payload={
                "message": {
                    "content": " Bonjour depuis Ollama. ",
                }
            }
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    model = OllamaChatModel()

    reply = model.generate_reply(
        model="qwen2.5:1.5b",
        message="Bonjour",
    )

    assert reply == "Bonjour depuis Ollama."


def test_generate_reply_maps_http_errors(
    monkeypatch,
) -> None:
    """Raise a chatbot error when Ollama cannot be reached."""

    def fake_post(
        url: str,
        *,
        json: dict,
        timeout: float,
    ) -> FakeResponse:
        raise httpx.ConnectError(
            "Connection refused",
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    model = OllamaChatModel()

    with pytest.raises(
        OllamaChatError,
        match="Unable to communicate with Ollama",
    ):
        model.generate_reply(
            model="qwen2.5:1.5b",
            message="Bonjour",
        )


def test_generate_reply_rejects_invalid_response(
    monkeypatch,
) -> None:
    """Reject malformed responses returned by Ollama."""

    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: FakeResponse(
            payload={"unexpected": "response"}
        ),
    )

    model = OllamaChatModel()

    with pytest.raises(
        OllamaChatError,
        match="Ollama returned an invalid response",
    ):
        model.generate_reply(
            model="qwen2.5:1.5b",
            message="Bonjour",
        )


def test_generate_reply_rejects_empty_response(
    monkeypatch,
) -> None:
    """Reject empty generated text returned by Ollama."""

    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: FakeResponse(
            payload={
                "message": {
                    "content": "   ",
                }
            }
        ),
    )

    model = OllamaChatModel()

    with pytest.raises(
        OllamaChatError,
        match="Ollama returned an empty response",
    ):
        model.generate_reply(
            model="qwen2.5:1.5b",
            message="Bonjour",
        )