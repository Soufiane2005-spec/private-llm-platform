"""Tests for Ollama streaming benchmark execution."""

import json

from infrastructure.llm.ollama_benchmark_executor import OllamaBenchmarkExecutor


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
                json.dumps({"done": True}),
            ]
        )


def test_ollama_benchmark_executor_measures_streaming_ttft(monkeypatch) -> None:
    """Streaming chunks produce total latency, TTFT, and token count."""

    ticks = iter([10.0, 10.25, 11.0])

    def fake_clock() -> float:
        return next(ticks)

    def fake_stream(*args, **kwargs):
        return FakeStreamResponse()

    monkeypatch.setattr(
        "infrastructure.llm.ollama_benchmark_executor.httpx.stream",
        fake_stream,
    )

    executor = OllamaBenchmarkExecutor(clock=fake_clock)

    result = executor.execute(
        model="llama3.2:1b",
        prompt="hello",
    )

    assert result.total_latency_ms == 1000.0
    assert result.ttft_ms == 250.0
    assert result.tokens_generated == 2
    assert result.duration_seconds == 1.0
