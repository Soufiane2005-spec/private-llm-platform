"""Deterministic policy for selecting an LLM engine deployment."""

from collections.abc import Sequence

from domain.models.llm_engine import (
    EngineCapability,
    EngineDeploymentProfile,
    EngineSelection,
    EngineSelectionRequest,
    LLMEngine,
)


class NoCompatibleEngineError(RuntimeError):
    """Raised when no configured engine satisfies the hard requirements."""


OLLAMA_PROFILE = EngineDeploymentProfile(
    engine=LLMEngine.OLLAMA,
    capabilities=frozenset(
        {
            EngineCapability.CPU_FALLBACK,
            EngineCapability.LOCAL_DEVELOPMENT,
            EngineCapability.NATIVE_MODEL_MANAGEMENT,
            EngineCapability.OPENAI_COMPATIBLE_API,
        }
    ),
    requires_nvidia_gpu=False,
)

VLLM_PROFILE = EngineDeploymentProfile(
    engine=LLMEngine.VLLM,
    capabilities=frozenset(
        {
            EngineCapability.CONTINUOUS_BATCHING,
            EngineCapability.HIGH_THROUGHPUT_SERVING,
            EngineCapability.OPENAI_COMPATIBLE_API,
        }
    ),
    requires_nvidia_gpu=True,
)

DEFAULT_ENGINE_PROFILES = (OLLAMA_PROFILE, VLLM_PROFILE)

_ENGINE_TIE_BREAK_ORDER = {
    LLMEngine.OLLAMA: 0,
    LLMEngine.VLLM: 1,
}


def select_engine(
    request: EngineSelectionRequest,
    profiles: Sequence[EngineDeploymentProfile] = DEFAULT_ENGINE_PROFILES,
) -> EngineSelection:
    """Select the best compatible deployment for the supplied request."""

    _validate_profiles(profiles)

    eligible_profiles = tuple(
        profile
        for profile in profiles
        if _is_eligible(profile=profile, request=request)
    )

    if not eligible_profiles:
        required = ", ".join(
            sorted(capability.value for capability in request.required_capabilities)
        )
        required_description = required or "none"
        raise NoCompatibleEngineError(
            "No engine deployment satisfies the request "
            f"(required capabilities: {required_description}, "
            f"NVIDIA GPU available: {request.nvidia_gpu_available})."
        )

    selected_profile = min(
        eligible_profiles,
        key=lambda profile: (
            -_preference_score(profile=profile, request=request),
            _ENGINE_TIE_BREAK_ORDER[profile.engine],
        ),
    )

    matched_preferences = (
        selected_profile.capabilities & request.preferred_capabilities
    )
    rationale = _build_rationale(
        profile=selected_profile,
        request=request,
        matched_preferences=matched_preferences,
    )

    return EngineSelection(
        engine=selected_profile.engine,
        score=len(matched_preferences),
        matched_preferences=matched_preferences,
        rationale=rationale,
    )


def _is_eligible(
    profile: EngineDeploymentProfile,
    request: EngineSelectionRequest,
) -> bool:
    has_required_hardware = (
        not profile.requires_nvidia_gpu or request.nvidia_gpu_available
    )
    return has_required_hardware and profile.supports(
        request.required_capabilities
    )


def _preference_score(
    profile: EngineDeploymentProfile,
    request: EngineSelectionRequest,
) -> int:
    return len(profile.capabilities & request.preferred_capabilities)


def _build_rationale(
    profile: EngineDeploymentProfile,
    request: EngineSelectionRequest,
    matched_preferences: frozenset[EngineCapability],
) -> tuple[str, ...]:
    rationale = ["all required capabilities are satisfied"]

    if profile.requires_nvidia_gpu:
        rationale.append("the required NVIDIA GPU is available")

    if matched_preferences:
        names = ", ".join(
            sorted(capability.value for capability in matched_preferences)
        )
        rationale.append(f"matched preferences: {names}")
    elif not request.preferred_capabilities:
        rationale.append("selected by the deterministic default order")

    return tuple(rationale)


def _validate_profiles(
    profiles: Sequence[EngineDeploymentProfile],
) -> None:
    if not profiles:
        raise ValueError("At least one engine deployment profile is required.")

    engines = tuple(profile.engine for profile in profiles)
    if len(engines) != len(set(engines)):
        raise ValueError("Engine deployment profiles must have unique engines.")