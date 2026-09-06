"""vLLM OpenAI-compatible benchmark executor."""

from collections.abc import Callable
from json import JSONDecodeError
from time import perf_counter

import httpx

from application.ports.benchmark_executor import BenchmarkExecution, BenchmarkExecutor


class VLLMBenchmarkError(RuntimeError):
    """Raised when vLLM benchmark execution fails."""


class VLLMBenchmarkExecutor(BenchmarkExecutor):
    """Benchmark vLLM chat completions through its OpenAI-compatible API."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8000",
        timeout_seconds: float = 120.0,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._clock = clock

    def execute(self, *, model: str, prompt: str) -> BenchmarkExecution:
        """Run one prompt through vLLM and return measured performance."""

        self._ensure_model_available(model)

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 96,
            "temperature": 0.0,
            "stream": False,
        }
        started_at = self._clock()

        try:
            response = httpx.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            detail = self._response_detail(exc.response)
            raise VLLMBenchmarkError(
                f"vLLM benchmark request failed with HTTP "
                f"{exc.response.status_code}: {detail}"
            ) from exc
        except (httpx.RequestError, JSONDecodeError, ValueError) as exc:
            raise VLLMBenchmarkError(
                f"Unable to execute benchmark against vLLM at {self._base_url}: {exc}"
            ) from exc

        completed_at = self._clock()
        latency_seconds = max(completed_at - started_at, 0.000001)
        usage = body.get("usage", {}) if isinstance(body, dict) else {}

        completion_tokens = self._positive_int(usage.get("completion_tokens"))
        prompt_tokens = self._positive_int(usage.get("prompt_tokens"))

        if completion_tokens is None:
            completion_tokens = self._estimate_completion_tokens(body)

        return BenchmarkExecution(
            total_latency_ms=latency_seconds * 1000,
            ttft_ms=latency_seconds * 1000,
            tokens_generated=completion_tokens,
            duration_seconds=latency_seconds,
            prompt_tokens=prompt_tokens,
            prompt_eval_duration_seconds=None,
        )

    def _ensure_model_available(self, model: str) -> None:
        try:
            response = httpx.get(
                f"{self._base_url}/v1/models",
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            detail = self._response_detail(exc.response)
            raise VLLMBenchmarkError(
                f"Unable to list vLLM models: HTTP "
                f"{exc.response.status_code}: {detail}"
            ) from exc
        except (httpx.RequestError, JSONDecodeError, ValueError) as exc:
            raise VLLMBenchmarkError(
                f"Unable to list vLLM models at {self._base_url}: {exc}"
            ) from exc

        models = {
            item.get("id")
            for item in body.get("data", [])
            if isinstance(item, dict)
        }

        if model not in models:
            available = ", ".join(sorted(name for name in models if name))
            suffix = f" Available models: {available}." if available else ""
            raise VLLMBenchmarkError(f"Model not available in vLLM: {model}.{suffix}")

    @staticmethod
    def _positive_int(value: object) -> int | None:
        if isinstance(value, int) and value >= 0:
            return value

        return None

    @staticmethod
    def _estimate_completion_tokens(body: object) -> int:
        if not isinstance(body, dict):
            return 0

        choices = body.get("choices", [])
        if not isinstance(choices, list) or not choices:
            return 0

        first = choices[0]
        if not isinstance(first, dict):
            return 0

        message = first.get("message", {})
        if not isinstance(message, dict):
            return 0

        content = message.get("content", "")
        return len(content.split()) if isinstance(content, str) else 0

    @staticmethod
    def _response_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text[:300]

        if isinstance(body, dict):
            detail = body.get("detail") or body.get("error")
            if detail:
                return str(detail)

        return str(body)[:300]
