"""Unit tests for the LLM engine selection policy."""

import pytest

from domain.models.llm_engine import (
    EngineCapability,
    EngineSelectionRequest,
    LLMEngine,
)
from domain.recommendations.engine_selector import (
    OLLAMA_PROFILE,
    NoCompatibleEngineError,
    select_engine,
)


def test_selects_ollama_by_default_without_gpu() -> None:
    request = EngineSelectionRequest(nvidia_gpu_available=False)

    result = select_engine(request)

    assert result.engine is LLMEngine.OLLAMA
    assert result.score == 0
    assert result.rationale == (
        "all required capabilities are satisfied",
        "selected by the deterministic default order",
    )


def test_selects_ollama_by_default_when_both_engines_are_available() -> None:
    request = EngineSelectionRequest(nvidia_gpu_available=True)

    result = select_engine(request)

    assert result.engine is LLMEngine.OLLAMA


def test_selects_vllm_for_throughput_preferences_with_gpu() -> None:
    preferences = frozenset(
        {
            EngineCapability.CONTINUOUS_BATCHING,
            EngineCapability.HIGH_THROUGHPUT_SERVING,
        }
    )
    request = EngineSelectionRequest(
        nvidia_gpu_available=True,
        preferred_capabilities=preferences,
    )

    result = select_engine(request)

    assert result.engine is LLMEngine.VLLM
    assert result.score == 2
    assert result.matched_preferences == preferences
    assert "the required NVIDIA GPU is available" in result.rationale


def test_selects_ollama_for_local_development() -> None:
    request = EngineSelectionRequest(
        nvidia_gpu_available=True,
        preferred_capabilities=frozenset(
            {EngineCapability.LOCAL_DEVELOPMENT}
        ),
    )

    result = select_engine(request)

    assert result.engine is LLMEngine.OLLAMA
    assert result.score == 1


def test_selects_ollama_for_openai_api_without_gpu() -> None:
    request = EngineSelectionRequest(
        nvidia_gpu_available=False,
        required_capabilities=frozenset(
            {EngineCapability.OPENAI_COMPATIBLE_API}
        ),
    )

    result = select_engine(request)

    assert result.engine is LLMEngine.OLLAMA


def test_rejects_gpu_only_requirement_without_gpu() -> None:
    request = EngineSelectionRequest(
        nvidia_gpu_available=False,
        required_capabilities=frozenset(
            {EngineCapability.HIGH_THROUGHPUT_SERVING}
        ),
    )

    with pytest.raises(
        NoCompatibleEngineError,
        match="No engine deployment satisfies the request",
    ):
        select_engine(request)


def test_ignores_unavailable_preference_without_failing() -> None:
    request = EngineSelectionRequest(
        nvidia_gpu_available=False,
        preferred_capabilities=frozenset(
            {EngineCapability.CONTINUOUS_BATCHING}
        ),
    )

    result = select_engine(request)

    assert result.engine is LLMEngine.OLLAMA
    assert result.score == 0
    assert result.rationale == ("all required capabilities are satisfied",)


def test_rejects_overlapping_required_and_preferred_capabilities() -> None:
    capability = EngineCapability.OPENAI_COMPATIBLE_API

    with pytest.raises(
        ValueError,
        match="Capabilities cannot be both required and preferred",
    ):
        EngineSelectionRequest(
            nvidia_gpu_available=True,
            required_capabilities=frozenset({capability}),
            preferred_capabilities=frozenset({capability}),
        )


def test_rejects_empty_profile_collection() -> None:
    request = EngineSelectionRequest(nvidia_gpu_available=True)

    with pytest.raises(
        ValueError,
        match="At least one engine deployment profile is required",
    ):
        select_engine(request=request, profiles=())


def test_rejects_duplicate_engine_profiles() -> None:
    request = EngineSelectionRequest(nvidia_gpu_available=True)

    with pytest.raises(
        ValueError,
        match="Engine deployment profiles must have unique engines",
    ):
        select_engine(
            request=request,
            profiles=(OLLAMA_PROFILE, OLLAMA_PROFILE),
        )


def test_profile_supports_only_known_capabilities() -> None:
    assert OLLAMA_PROFILE.supports(
        frozenset({EngineCapability.CPU_FALLBACK})
    )
    assert not OLLAMA_PROFILE.supports(
        frozenset({EngineCapability.CONTINUOUS_BATCHING})
    )