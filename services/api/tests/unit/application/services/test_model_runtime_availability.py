"""Tests for live runtime availability and benchmark eligibility."""

import httpx
import pytest

from application.services.model_runtime_availability import ModelRuntimeAvailability
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry


def ollama_model(*, enabled: bool = True) -> ModelCatalogEntry:
    return ModelCatalogEntry(
        model_id="phi3-mini",
        display_name="Phi-3 Mini",
        engine=LLMEngine.OLLAMA,
        engine_model_id="phi3:mini",
        enabled=enabled,
    )


def vllm_model() -> ModelCatalogEntry:
    return ModelCatalogEntry(
        model_id="smollm2-135m",
        display_name="SmolLM2 135M",
        engine=LLMEngine.VLLM,
        engine_model_id="HuggingFaceTB/SmolLM2-135M-Instruct",
        served_model_name="smollm2-135m",
        gpu_required=True,
    )


def checker(client: httpx.Client | None = None) -> ModelRuntimeAvailability:
    return ModelRuntimeAvailability(
        ollama_base_url="http://ollama:11434",
        vllm_base_url="http://vllm:8000",
        client=client,
    )


def mock_client(handler) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(handler),
        timeout=1.0,
        trust_env=False,
    )


def test_ollama_runtime_available_uses_real_tag_listing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://ollama:11434/api/tags"
        return httpx.Response(
            200,
            json={"models": [{"name": "phi3:mini"}]},
            request=request,
        )

    state = checker(mock_client(handler)).state_for(ollama_model())

    assert state.runtime_available is True
    assert state.benchmark_eligible is True


def test_ollama_runtime_available_treats_untagged_model_as_latest(
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://ollama:11434/api/tags"
        return httpx.Response(
            200,
            json={"models": [{"name": "tinyllama:latest"}]},
            request=request,
        )

    state = checker(mock_client(handler)).state_for(
        ModelCatalogEntry(
            model_id="tinyllama",
            display_name="TinyLlama",
            engine=LLMEngine.OLLAMA,
            engine_model_id="tinyllama",
        )
    )

    assert state.runtime_available is True
    assert state.benchmark_eligible is True


def test_vllm_runtime_available_uses_served_model_listing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://vllm:8000/v1/models"
        return httpx.Response(
            200,
            json={"data": [{"id": "smollm2-135m"}]},
            request=request,
        )

    state = checker(mock_client(handler)).state_for(vllm_model())

    assert state.runtime_available is True
    assert state.benchmark_eligible is True


def test_unavailable_runtime_is_not_benchmark_eligible() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"models": [{"name": "qwen2.5:1.5b"}]},
            request=request,
        )

    client = mock_client(handler)

    state = checker(client).state_for(ollama_model())

    assert state.runtime_available is False
    assert state.benchmark_eligible is False
    with pytest.raises(ValueError, match="not benchmark eligible"):
        checker(client).require_benchmark_eligible(ollama_model())


def test_disabled_model_is_not_benchmark_eligible_without_runtime_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("disabled models should not query runtimes")

    state = checker(mock_client(handler)).state_for(ollama_model(enabled=False))

    assert state.runtime_available is False
    assert state.benchmark_eligible is False
    assert state.reason == "model is disabled"


def test_runtime_listing_failures_are_cached_per_checker() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("connection refused", request=request)

    runtime_checker = checker(mock_client(handler))
    first = runtime_checker.state_for(vllm_model())
    second = runtime_checker.state_for(vllm_model())

    assert first.runtime_available is False
    assert second.runtime_available is False
    assert calls == 1
