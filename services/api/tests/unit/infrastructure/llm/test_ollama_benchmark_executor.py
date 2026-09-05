"""Tests for Ollama streaming benchmark execution."""

import json

import httpx
import pytest

from infrastructure.llm.ollama_benchmark_executor import (
    OllamaBenchmarkError,
    OllamaBenchmarkExecutor,
)


class FakeStreamResponse:
    """Minimal httpx stream response fake."""

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        return iter(
            [
                json.dumps({"response": "hello"}),
                json.dumps({"response": " world"}),
                json.dumps(
                    {
                        "done": True,
                        "eval_count": 8,
                        "eval_duration": 500_000_000,
                        "prompt_eval_count": 3,
                        "prompt_eval_duration": 100_000_000,
                    }
                ),
            ]
        )


def test_ollama_benchmark_executor_measures_streaming_ttft(monkeypatch) -> None:
    """Streaming chunks produce total latency, TTFT, and token count."""

    ticks = iter([10.0, 10.25, 11.0])

    def fake_clock() -> float:
        return next(ticks)

    def fake_stream(*args, **kwargs):
        return FakeStreamResponse()

    def fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"models": [{"name": "qwen2.5:1.5b"}]},
            request=httpx.Request("GET", "http://ollama:11434/api/tags"),
        )

    monkeypatch.setattr(
        "infrastructure.llm.ollama_benchmark_executor.httpx.stream",
        fake_stream,
    )
    monkeypatch.setattr(
        "infrastructure.llm.ollama_benchmark_executor.httpx.get",
        fake_get,
    )

    executor = OllamaBenchmarkExecutor(clock=fake_clock)

    result = executor.execute(
        model="qwen2.5:1.5b",
        prompt="hello",
    )

    assert result.total_latency_ms == 1000.0
    assert result.ttft_ms == 250.0
    assert result.tokens_generated == 8
    assert result.duration_seconds == 0.5
    assert result.prompt_tokens == 3
    assert result.prompt_eval_duration_seconds == 0.1


def test_ollama_benchmark_executor_rejects_missing_model(monkeypatch) -> None:
    def fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"models": [{"name": "qwen2.5:1.5b"}]},
            request=httpx.Request("GET", "http://ollama:11434/api/tags"),
        )

    monkeypatch.setattr(
        "infrastructure.llm.ollama_benchmark_executor.httpx.get",
        fake_get,
    )

    executor = OllamaBenchmarkExecutor()

    with pytest.raises(OllamaBenchmarkError, match="Model not available"):
        executor.execute(model="llama3.2:1b", prompt="hello")
