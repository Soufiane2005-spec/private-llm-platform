"""Port for provisioning models inside a running Ollama runtime."""

from typing import Protocol


class OllamaRuntimeClient(Protocol):
    """Query and provision models available to an Ollama runtime."""

    def has_model(self, model: str) -> bool:
        """Return whether a model tag is currently available in Ollama."""

    def pull_model(self, model: str) -> None:
        """Pull (download) a model into the Ollama runtime.

        Implementations should raise on failure so callers can surface a
        useful, model-specific error instead of silently succeeding.
        """

    def ensure_model_available(self, model: str) -> bool:
        """Ensure a model tag is present in Ollama, pulling it if absent.

        Returns ``True`` when a pull was actually performed and ``False``
        when the model was already present (idempotent no-op).
        """
