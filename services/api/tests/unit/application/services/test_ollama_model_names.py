"""Tests for Ollama model name normalization."""

from application.services.ollama_model_names import (
    ollama_model_aliases,
    ollama_models_match,
)


def test_untagged_model_matches_latest_tag() -> None:
    assert ollama_models_match("tinyllama", "tinyllama:latest")
    assert ollama_model_aliases("tinyllama") == {"tinyllama", "tinyllama:latest"}


def test_explicit_tag_is_preserved() -> None:
    assert ollama_model_aliases("phi3:mini") == {"phi3:mini"}
    assert ollama_models_match("phi3:mini", "phi3:mini")


def test_explicit_tag_does_not_match_latest() -> None:
    assert not ollama_models_match("phi3:mini", "phi3:latest")
