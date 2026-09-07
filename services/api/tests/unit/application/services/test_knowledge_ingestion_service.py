"""Tests for explicit local knowledge ingestion."""

from pathlib import Path

import pytest

from application.services.knowledge_ingestion_service import KnowledgeIngestionService


def test_ingest_text_writes_safe_project_local_document(tmp_path: Path) -> None:
    service = KnowledgeIngestionService(tmp_path)

    result = service.ingest_text(
        source="../unsafe name",
        content="Article 101 Terrassement: quantite prevue 500 m3.",
    )

    assert result.source == "unsafe-name.txt"
    assert (tmp_path / result.source).read_text(encoding="utf-8").startswith(
        "Article 101"
    )


def test_ingest_text_rejects_empty_content(tmp_path: Path) -> None:
    service = KnowledgeIngestionService(tmp_path)

    with pytest.raises(ValueError, match="content cannot be empty"):
        service.ingest_text(source="empty.md", content=" ")
