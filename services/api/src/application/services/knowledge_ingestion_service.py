"""Explicit local knowledge ingestion for the RAG service."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class IngestedKnowledgeDocument:
    """Summary of a document ingested into local knowledge storage."""

    source: str
    bytes_written: int


class KnowledgeIngestionService:
    """Persist approved text knowledge into a project-local directory."""

    def __init__(self, knowledge_directory: Path) -> None:
        self._knowledge_directory = knowledge_directory

    def ingest_text(self, *, source: str, content: str) -> IngestedKnowledgeDocument:
        """Write a text/Markdown document for later retrieval."""

        clean_source = self._safe_source_name(source)
        clean_content = content.strip()

        if not clean_content:
            raise ValueError("content cannot be empty.")

        self._knowledge_directory.mkdir(parents=True, exist_ok=True)
        target = self._knowledge_directory / clean_source
        target.write_text(f"{clean_content}\n", encoding="utf-8")

        return IngestedKnowledgeDocument(
            source=clean_source,
            bytes_written=target.stat().st_size,
        )

    @staticmethod
    def _safe_source_name(source: str) -> str:
        clean = source.strip()
        if not clean:
            raise ValueError("source cannot be empty.")

        name = Path(clean).name
        stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip(".-")

        if not stem:
            raise ValueError("source cannot be empty.")

        if Path(stem).suffix.lower() not in {".md", ".txt"}:
            stem = f"{stem}.txt"

        return stem[:180]
