"""Ollama streaming benchmark executor."""

import json
from collections.abc import Callable
from time import perf_counter

import httpx

from application.ports.benchmark_executor import BenchmarkExecution, BenchmarkExecutor


class OllamaBenchmarkError(RuntimeError):
    """Raised when Ollama benchmark execution fails."""


class OllamaBenchmarkExecutor(BenchmarkExecutor):
    """Benchmark Ollama generation with streaming TTFT measurement."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 120.0,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._clock = clock

    def execute(self, *, model: str, prompt: str) -> BenchmarkExecution:
        """Run one prompt through Ollama streaming generation."""

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }
        started_at = self._clock()
        first_token_at: float | None = None
        generated_text = ""

        try:
            with httpx.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout_seconds,
            ) as response:
                response.raise_for_status()

                for chunk in response.iter_lines():
                    if not chunk:
                        continue

                    data = json.loads(chunk)
                    token = data.get("response", "")

                    if token and first_token_at is None:
                        first_token_at = self._clock()

                    if isinstance(token, str):
                        generated_text += token

                    if data.get("done") is True:
                        break
        except Exception as exc:
            raise OllamaBenchmarkError(
                "Unable to execute streaming benchmark against Ollama."
            ) from exc

        finished_at = self._clock()
        duration_seconds = finished_at - started_at

        if duration_seconds <= 0:
            duration_seconds = 0.000001

        ttft_ms = (
            0.0
            if first_token_at is None
            else (first_token_at - started_at) * 1000
        )

        return BenchmarkExecution(
            total_latency_ms=duration_seconds * 1000,
            ttft_ms=ttft_ms,
            tokens_generated=max(len(generated_text.split()), 0),
            duration_seconds=duration_seconds,
        )
