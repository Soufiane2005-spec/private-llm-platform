"""Local file-based knowledge retriever for the RAG MVP."""

import re
import unicodedata
from pathlib import Path

from application.ports.knowledge_retriever import KnowledgeMatch

DEFAULT_KNOWLEDGE_DIRECTORY = (
    Path(__file__).resolve().parents[3] / "data" / "knowledge"
)

SUPPORTED_EXTENSIONS = {".md", ".txt"}

STOP_WORDS = {
    "a",
    "au",
    "aux",
    "avec",
    "ce",
    "ces",
    "dans",
    "de",
    "des",
    "du",
    "elle",
    "en",
    "et",
    "est",
    "il",
    "je",
    "la",
    "le",
    "les",
    "ma",
    "mais",
    "mes",
    "mon",
    "ne",
    "nous",
    "ou",
    "par",
    "pas",
    "pour",
    "que",
    "qui",
    "sa",
    "se",
    "ses",
    "son",
    "sur",
    "un",
    "une",
    "vous",
}


class LocalKnowledgeRetriever:
    """Retrieve relevant text chunks from local Markdown and text files."""

    def __init__(
        self,
        knowledge_directory: Path = DEFAULT_KNOWLEDGE_DIRECTORY,
    ) -> None:
        self._knowledge_directory = knowledge_directory

    def search(
        self,
        query: str,
        *,
        limit: int = 3,
    ) -> list[KnowledgeMatch]:
        """Search local documentation using lexical token similarity."""

        if limit <= 0:
            return []

        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        matches: list[KnowledgeMatch] = []

        for path in self._knowledge_files():
            content = path.read_text(encoding="utf-8")

            for chunk in self._split_into_chunks(content):
                chunk_tokens = self._tokenize(chunk)

                if not chunk_tokens:
                    continue

                common_tokens = query_tokens & chunk_tokens

                if not common_tokens:
                    continue

                score = len(common_tokens) / len(query_tokens)

                matches.append(
                    KnowledgeMatch(
                        source=path.name,
                        content=chunk.strip(),
                        score=score,
                    )
                )

        matches.sort(
            key=lambda match: match.score,
            reverse=True,
        )

        return matches[:limit]

    def _knowledge_files(self) -> list[Path]:
        if not self._knowledge_directory.exists():
            return []

        return sorted(
            path
            for path in self._knowledge_directory.iterdir()
            if path.is_file()
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    @staticmethod
    def _split_into_chunks(content: str) -> list[str]:
        return [
            chunk.strip()
            for chunk in re.split(r"\n\s*\n", content)
            if chunk.strip()
        ]

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.lower())

        return "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        normalized_text = cls._normalize_text(text)

        tokens = re.findall(
            r"\b\w+\b",
            normalized_text,
            flags=re.UNICODE,
        )

        return {
            token
            for token in tokens
            if len(token) > 2
            and token not in STOP_WORDS
        }