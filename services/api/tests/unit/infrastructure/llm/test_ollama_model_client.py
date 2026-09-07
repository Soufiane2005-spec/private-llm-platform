"""Tests for the Ollama runtime model management client."""

import json

import httpx
import pytest

from infrastructure.llm.ollama_model_client import (
    OllamaModelClient,
    OllamaModelClientError,
)


class FakePullResponse:
    """Minimal httpx streaming response fake for /api/pull."""

    def __init__(self, events: list[dict]) -> None:
        self._events = events

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        return iter(json.dumps(event) for event in self._events)


def test_list_model_names_returns_tags(monkeypatch) -> None:
    """Listing models parses the Ollama /api/tags payload."""

    def fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"models": [{"name": "qwen2.5:1.5b"}, {"name": "phi3:mini"}]},
            request=httpx.Request("GET", "http://ollama:11434/api/tags"),
        )

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.get", fake_get
    )

    client = OllamaModelClient()

    assert client.list_model_names() == {"qwen2.5:1.5b", "phi3:mini"}
    assert client.has_model("phi3:mini") is True
    assert client.has_model("llama3.2:1b") is False


def test_has_model_treats_untagged_model_as_latest(monkeypatch) -> None:
    """Ollama's implicit latest tag satisfies an untagged catalog id."""

    def fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"models": [{"name": "tinyllama:latest"}]},
            request=httpx.Request("GET", "http://ollama:11434/api/tags"),
        )

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.get", fake_get
    )

    client = OllamaModelClient()

    assert client.has_model("tinyllama") is True
    assert client.has_model("tinyllama:latest") is True
    assert client.has_model("tinyllama:1.1b") is False


def test_list_model_names_raises_on_connection_error(monkeypatch) -> None:
    """Unreachable Ollama raises a clear client error."""

    def fake_get(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.get", fake_get
    )

    client = OllamaModelClient()

    with pytest.raises(OllamaModelClientError):
        client.list_model_names()


def test_pull_model_succeeds_on_completion_status(monkeypatch) -> None:
    """A successful pull stream marks the model as provisioned."""

    def fake_stream(*args, **kwargs):
        return FakePullResponse(
            [
                {"status": "pulling manifest"},
                {"status": "success"},
            ]
        )

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.stream", fake_stream
    )

    client = OllamaModelClient()
    client.pull_model("phi3:mini")


def test_pull_model_raises_on_error_event(monkeypatch) -> None:
    """An error event in the pull stream is surfaced as a client error."""

    def fake_stream(*args, **kwargs):
        return FakePullResponse([{"error": "model not found"}])

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.stream", fake_stream
    )

    client = OllamaModelClient()

    with pytest.raises(OllamaModelClientError, match="model not found"):
        client.pull_model("phi3:mini")


def test_ensure_model_available_skips_pull_when_present(monkeypatch) -> None:
    """ensure_model_available is a no-op when the model is already present."""

    calls = {"tags": 0, "pull": 0}

    def fake_get(*args, **kwargs):
        calls["tags"] += 1
        return httpx.Response(
            200,
            json={"models": [{"name": "phi3:mini"}]},
            request=httpx.Request("GET", "http://ollama:11434/api/tags"),
        )

    def fake_stream(*args, **kwargs):
        calls["pull"] += 1
        return FakePullResponse([{"status": "success"}])

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.get", fake_get
    )
    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.stream", fake_stream
    )

    client = OllamaModelClient()
    pulled = client.ensure_model_available("phi3:mini")

    assert pulled is False
    assert calls["pull"] == 0


def test_ensure_model_available_pulls_when_absent(monkeypatch) -> None:
    """ensure_model_available pulls the model when it is not yet present."""

    tag_responses = iter(
        [
            {"models": []},
            {"models": [{"name": "phi3:mini"}]},
        ]
    )

    def fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json=next(tag_responses),
            request=httpx.Request("GET", "http://ollama:11434/api/tags"),
        )

    def fake_stream(*args, **kwargs):
        return FakePullResponse([{"status": "success"}])

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.get", fake_get
    )
    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.stream", fake_stream
    )

    client = OllamaModelClient()
    pulled = client.ensure_model_available("phi3:mini")

    assert pulled is True


def test_ensure_model_available_accepts_latest_after_untagged_pull(
    monkeypatch,
) -> None:
    """Post-pull verification accepts Ollama's implicit :latest runtime tag."""

    tag_responses = iter(
        [
            {"models": []},
            {"models": [{"name": "tinyllama:latest"}]},
        ]
    )

    def fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json=next(tag_responses),
            request=httpx.Request("GET", "http://ollama:11434/api/tags"),
        )

    def fake_stream(*args, **kwargs):
        return FakePullResponse([{"status": "success"}])

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.get", fake_get
    )
    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.stream", fake_stream
    )

    client = OllamaModelClient()

    assert client.ensure_model_available("tinyllama") is True


def test_ensure_model_available_fails_if_still_missing_after_pull(monkeypatch) -> None:
    """A pull that reports success but leaves the model missing is an error."""

    def fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"models": []},
            request=httpx.Request("GET", "http://ollama:11434/api/tags"),
        )

    def fake_stream(*args, **kwargs):
        return FakePullResponse([{"status": "success"}])

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.get", fake_get
    )
    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.stream", fake_stream
    )

    client = OllamaModelClient()

    with pytest.raises(OllamaModelClientError, match="still not listed"):
        client.ensure_model_available("phi3:mini")
def test_list_model_names_raises_on_http_error(monkeypatch) -> None:
    """HTTP failures while listing models include Ollama's error detail."""

    def fake_get(*args, **kwargs):
        return httpx.Response(
            503,
            json={"error": "runtime unavailable"},
            request=httpx.Request(
                "GET",
                "http://127.0.0.1:11434/api/tags",
            ),
        )

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.get",
        fake_get,
    )

    client = OllamaModelClient()

    with pytest.raises(
        OllamaModelClientError,
        match="HTTP 503: runtime unavailable",
    ):
        client.list_model_names()


def test_pull_model_ignores_empty_invalid_and_non_dict_events(
    monkeypatch,
) -> None:
    """Malformed pull events are ignored when valid progress follows."""

    class MixedPullResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_lines(self):
            return iter(
                [
                    "",
                    "not-json",
                    json.dumps(["not", "a", "dict"]),
                    json.dumps({"status": "success"}),
                ]
            )

    def fake_stream(*args, **kwargs):
        return MixedPullResponse()

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.stream",
        fake_stream,
    )

    client = OllamaModelClient()

    client.pull_model("phi3:mini")


def test_pull_model_fails_when_no_progress_is_reported(monkeypatch) -> None:
    """A pull stream without a status event is considered invalid."""

    def fake_stream(*args, **kwargs):
        return FakePullResponse([])

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.stream",
        fake_stream,
    )

    client = OllamaModelClient()

    with pytest.raises(
        OllamaModelClientError,
        match="did not report any progress",
    ):
        client.pull_model("phi3:mini")


def test_pull_model_wraps_connection_error(monkeypatch) -> None:
    """Network failures during a pull become Ollama client errors."""

    request = httpx.Request(
        "POST",
        "http://127.0.0.1:11434/api/pull",
    )

    def fake_stream(*args, **kwargs):
        raise httpx.ConnectError(
            "connection refused",
            request=request,
        )

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.stream",
        fake_stream,
    )

    client = OllamaModelClient()

    with pytest.raises(
        OllamaModelClientError,
        match="Unable to reach Ollama",
    ):
        client.pull_model("phi3:mini")


def test_response_detail_uses_plain_text_when_response_is_not_json() -> None:
    """Non-JSON Ollama errors fall back to response text."""

    response = httpx.Response(
        500,
        text="plain Ollama failure",
        request=httpx.Request(
            "GET",
            "http://127.0.0.1:11434/api/tags",
        ),
    )

    assert (
        OllamaModelClient._response_detail(response)
        == "plain Ollama failure"
    )


def test_response_detail_falls_back_to_json_body_without_error() -> None:
    """JSON responses without an error field remain readable."""

    response = httpx.Response(
        400,
        json={"message": "invalid request"},
        request=httpx.Request(
            "GET",
            "http://127.0.0.1:11434/api/tags",
        ),
    )

    detail = OllamaModelClient._response_detail(response)

    assert "invalid request" in detail