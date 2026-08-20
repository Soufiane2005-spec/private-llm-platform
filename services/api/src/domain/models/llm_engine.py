"""Domain models used to compare supported LLM engine deployments."""

from dataclasses import dataclass
from enum import StrEnum


class LLMEngine(StrEnum):
    """LLM engines supported by the platform."""

    OLLAMA = "ollama"
    VLLM = "vllm"


class EngineCapability(StrEnum):
    """Capabilities relevant to engine selection."""

    CPU_FALLBACK = "cpu_fallback"
    LOCAL_DEVELOPMENT = "local_development"
    NATIVE_MODEL_MANAGEMENT = "native_model_management"
    OPENAI_COMPATIBLE_API = "openai_compatible_api"
    HIGH_THROUGHPUT_SERVING = "high_throughput_serving"
    CONTINUOUS_BATCHING = "continuous_batching"


@dataclass(frozen=True, slots=True)
class EngineDeploymentProfile:
    """Capabilities of an engine deployment supported by this repository."""

    engine: LLMEngine
    capabilities: frozenset[EngineCapability]
    requires_nvidia_gpu: bool

    def supports(self, required: frozenset[EngineCapability]) -> bool:
        """Return whether the deployment satisfies every required capability."""

        return required.issubset(self.capabilities)


@dataclass(frozen=True, slots=True)
class EngineSelectionRequest:
    """Hard requirements and preferences used to select an engine."""

    nvidia_gpu_available: bool
    required_capabilities: frozenset[EngineCapability] = frozenset()
    preferred_capabilities: frozenset[EngineCapability] = frozenset()

    def __post_init__(self) -> None:
        """Reject capabilities declared as both required and preferred."""

        overlap = self.required_capabilities & self.preferred_capabilities
        if overlap:
            names = ", ".join(sorted(capability.value for capability in overlap))
            raise ValueError(
                f"Capabilities cannot be both required and preferred: {names}"
            )


@dataclass(frozen=True, slots=True)
class EngineSelection:
    """Result returned by the engine selection policy."""

    engine: LLMEngine
    score: int
    matched_preferences: frozenset[EngineCapability]
    rationale: tuple[str, ...]