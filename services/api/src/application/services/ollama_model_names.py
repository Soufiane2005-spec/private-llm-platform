"""Helpers for comparing Ollama model names consistently."""


def ollama_model_aliases(model: str) -> set[str]:
    """Return acceptable runtime names for a requested Ollama model.

    Ollama stores untagged pulls such as ``tinyllama`` as
    ``tinyllama:latest``. Explicit tags such as ``phi3:mini`` stay exact.
    """

    normalized = model.strip()
    if not normalized:
        return set()

    if ":" in normalized:
        return {normalized}

    return {normalized, f"{normalized}:latest"}


def ollama_models_match(requested: str, runtime_name: str) -> bool:
    """Return whether a runtime model satisfies a requested Ollama name."""

    return runtime_name.strip() in ollama_model_aliases(requested)
