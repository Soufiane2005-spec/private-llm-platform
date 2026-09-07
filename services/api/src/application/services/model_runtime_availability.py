"""Runtime availability checks for catalog models."""

from dataclasses import dataclass
from json import JSONDecodeError

import httpx

from application.services.ollama_model_names import ollama_models_match
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry


@dataclass(frozen=True, slots=True)
class ModelRuntimeState:
    """Current live runtime state for a catalog model."""

    runtime_available: bool
    benchmark_eligible: bool
    reason: str | None = None


class ModelRuntimeAvailability:
    """Check whether catalog models are actually served by their engine."""

    def __init__(
        self,
        *,
        ollama_base_url: str,
        vllm_base_url: str,
        timeout_seconds: float = 2.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._ollama_base_url = ollama_base_url.rstrip("/")
        self._vllm_base_url = vllm_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            trust_env=False,
        )
        self._ollama_names: set[str] | None = None
        self._vllm_names: set[str] | None = None
        self._ollama_error: RuntimeError | None = None
        self._vllm_error: RuntimeError | None = None

    def state_for(self, model: ModelCatalogEntry) -> ModelRuntimeState:
        """Return live runtime and benchmark eligibility for a model."""

        if not model.enabled:
            return ModelRuntimeState(
                runtime_available=False,
                benchmark_eligible=False,
                reason="model is disabled",
            )

        try:
            available = self._runtime_available(model)
        except RuntimeError as exc:
            return ModelRuntimeState(
                runtime_available=False,
                benchmark_eligible=False,
                reason=str(exc),
            )

        if not available:
            return ModelRuntimeState(
                runtime_available=False,
                benchmark_eligible=False,
                reason=(
                    f"model '{model.benchmark_model_id}' is not available in "
                    f"{model.engine.value}"
                ),
            )

        return ModelRuntimeState(runtime_available=True, benchmark_eligible=True)

    def require_benchmark_eligible(self, model: ModelCatalogEntry) -> None:
        """Raise a useful error when a model cannot currently be benchmarked."""

        state = self.state_for(model)

        if state.benchmark_eligible:
            return

        detail = state.reason or "model is not benchmark eligible"
        raise ValueError(
            f"Model '{model.model_id}' is not benchmark eligible: {detail}."
        )

    def _runtime_available(self, model: ModelCatalogEntry) -> bool:
        if model.engine is LLMEngine.OLLAMA:
            return any(
                ollama_models_match(model.engine_model_id, runtime_name)
                for runtime_name in self._ollama_model_names()
            )

        if model.engine is LLMEngine.VLLM:
            return model.benchmark_model_id in self._vllm_model_names()

        raise RuntimeError(f"unsupported model engine '{model.engine.value}'")

    def _ollama_model_names(self) -> set[str]:
        if self._ollama_names is not None:
            return self._ollama_names
        if self._ollama_error is not None:
            raise self._ollama_error

        try:
            response = self._client.get(f"{self._ollama_base_url}/api/tags")
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            self._ollama_error = RuntimeError(
                f"unable to list Ollama models: HTTP {exc.response.status_code}"
            )
            raise self._ollama_error from exc
        except (httpx.RequestError, JSONDecodeError, ValueError) as exc:
            self._ollama_error = RuntimeError(
                f"unable to list Ollama models at {self._ollama_base_url}: {exc}"
            )
            raise self._ollama_error from exc

        self._ollama_names = {
            item.get("name")
            for item in body.get("models", [])
            if isinstance(item, dict) and item.get("name")
        }
        return self._ollama_names

    def _vllm_model_names(self) -> set[str]:
        if self._vllm_names is not None:
            return self._vllm_names
        if self._vllm_error is not None:
            raise self._vllm_error

        try:
            response = self._client.get(f"{self._vllm_base_url}/v1/models")
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            self._vllm_error = RuntimeError(
                f"unable to list vLLM models: HTTP {exc.response.status_code}"
            )
            raise self._vllm_error from exc
        except (httpx.RequestError, JSONDecodeError, ValueError) as exc:
            self._vllm_error = RuntimeError(
                f"unable to list vLLM models at {self._vllm_base_url}: {exc}"
            )
            raise self._vllm_error from exc

        self._vllm_names = {
            item.get("id")
            for item in body.get("data", [])
            if isinstance(item, dict) and item.get("id")
        }
        return self._vllm_names
