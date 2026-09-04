"""Unit tests for backend runtime configuration."""

from infrastructure.config import Settings


def test_settings_default_to_local_ollama_endpoint() -> None:
    """Local development should use the host Ollama endpoint by default."""

    settings = Settings(_env_file=None)

    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.ollama_timeout_seconds == 120.0


def test_settings_read_ollama_environment(monkeypatch) -> None:
    """Kubernetes can override the Ollama service endpoint."""

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "45.5")

    settings = Settings(_env_file=None)

    assert settings.ollama_base_url == "http://ollama:11434"
    assert settings.ollama_timeout_seconds == 45.5
