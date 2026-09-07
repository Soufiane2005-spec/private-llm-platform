"""Unit tests for the local RAG knowledge retriever."""

from pathlib import Path

from infrastructure.rag.local_knowledge_retriever import (
    LocalKnowledgeRetriever,
)


def test_search_returns_matching_document(
    tmp_path: Path,
) -> None:
    document = tmp_path / "irrigation.md"
    document.write_text(
        "Le dossier contient une localisation de l'exploitation "
        "et une description du problème d'irrigation.",
        encoding="utf-8",
    )

    retriever = LocalKnowledgeRetriever(tmp_path)

    results = retriever.search(
        "problème irrigation exploitation"
    )

    assert results
    assert results[0].source == "irrigation.md"
    assert results[0].chunk_index == 1


def test_search_returns_empty_for_unknown_query(
    tmp_path: Path,
) -> None:
    document = tmp_path / "faq.md"
    document.write_text(
        "Une demande possède un numéro de suivi.",
        encoding="utf-8",
    )

    retriever = LocalKnowledgeRetriever(tmp_path)

    results = retriever.search(
        "astronomie galaxie satellite"
    )

    assert results == []


def test_search_returns_empty_when_directory_missing(
    tmp_path: Path,
) -> None:
    retriever = LocalKnowledgeRetriever(
        tmp_path / "missing"
    )

    assert retriever.search("irrigation") == []


def test_search_preserves_page_metadata_when_present(
    tmp_path: Path,
) -> None:
    document = tmp_path / "decompte.md"
    document.write_text(
        "Decompte page 6. Total TTC declare 1 246 840 MAD.",
        encoding="utf-8",
    )

    retriever = LocalKnowledgeRetriever(tmp_path)

    results = retriever.search("total TTC declare")

    assert results[0].page == 6
