"""Ollama streaming benchmark executor."""

import json
from collections.abc import Callable
from json import JSONDecodeError
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

        self._ensure_model_available(model)

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }
        started_at = self._clock()
        first_token_at: float | None = None
        completed_at: float | None = None
        generated_text = ""
        eval_count: int | None = None
        eval_duration_ns: int | None = None
        prompt_eval_count: int | None = None
        prompt_eval_duration_ns: int | None = None

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
                        completed_at = self._clock()
                        eval_count = self._positive_int(data.get("eval_count"))
                        eval_duration_ns = self._positive_int(
                            data.get("eval_duration")
                        )
                        prompt_eval_count = self._positive_int(
                            data.get("prompt_eval_count")
                        )
                        prompt_eval_duration_ns = self._positive_int(
                            data.get("prompt_eval_duration")
                        )
                        break
        except httpx.HTTPStatusError as exc:
            detail = self._response_detail(exc.response)
            raise OllamaBenchmarkError(
                f"Ollama benchmark request failed with HTTP "
                f"{exc.response.status_code}: {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaBenchmarkError(
                f"Unable to reach Ollama at {self._base_url}: {exc}"
            ) from exc
        except JSONDecodeError as exc:
            raise OllamaBenchmarkError(
                "Ollama returned malformed streaming JSON."
            ) from exc
        except Exception as exc:
            raise OllamaBenchmarkError(
                f"Unable to execute streaming benchmark against Ollama: {exc}"
            ) from exc

        finished_at = completed_at or self._clock()
        latency_seconds = finished_at - started_at

        if latency_seconds <= 0:
            latency_seconds = 0.000001

        ttft_ms = (
            0.0
            if first_token_at is None
            else (first_token_at - started_at) * 1000
        )
        generated_tokens = eval_count or max(len(generated_text.split()), 0)
        token_duration_seconds = (
            eval_duration_ns / 1_000_000_000
            if eval_duration_ns is not None
            else latency_seconds
        )

        return BenchmarkExecution(
            total_latency_ms=latency_seconds * 1000,
            ttft_ms=ttft_ms,
            tokens_generated=generated_tokens,
            duration_seconds=max(token_duration_seconds, 0.000001),
            prompt_tokens=prompt_eval_count,
            prompt_eval_duration_seconds=(
                None
                if prompt_eval_duration_ns is None
                else prompt_eval_duration_ns / 1_000_000_000
            ),
        )

    def _ensure_model_available(self, model: str) -> None:
        try:
            response = httpx.get(
                f"{self._base_url}/api/tags",
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            detail = self._response_detail(exc.response)
            raise OllamaBenchmarkError(
                f"Unable to list Ollama models: HTTP "
                f"{exc.response.status_code}: {detail}"
            ) from exc
        except (httpx.RequestError, JSONDecodeError, ValueError) as exc:
            raise OllamaBenchmarkError(
                f"Unable to list Ollama models at {self._base_url}: {exc}"
            ) from exc

        models = {
            item.get("name")
            for item in body.get("models", [])
            if isinstance(item, dict)
        }

        if model not in models:
            available = ", ".join(sorted(name for name in models if name))
            suffix = f" Available models: {available}." if available else ""
            raise OllamaBenchmarkError(f"Model not available in Ollama: {model}.{suffix}")

    @staticmethod
    def _positive_int(value: object) -> int | None:
        if isinstance(value, int) and value > 0:
            return value

        return None

    @staticmethod
    def _response_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text[:300]

        if isinstance(body, dict):
            error = body.get("error")
            if error:
                return str(error)

        return str(body)[:300]
