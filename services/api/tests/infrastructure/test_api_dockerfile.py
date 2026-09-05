"""Tests for the API Docker image packaging contract."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
DOCKERFILE = ROOT_DIR / "services" / "api" / "Dockerfile"


def test_api_image_includes_rag_knowledge_files() -> None:
    """The API image must package local RAG demonstration documents."""

    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "COPY src ./src" in dockerfile
    assert "COPY data ./data" in dockerfile
