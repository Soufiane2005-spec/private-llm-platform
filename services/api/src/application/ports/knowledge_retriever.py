"""Knowledge retrieval application port."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class KnowledgeMatch:
    """Relevant knowledge passage returned by a retriever."""

    source: str
    content: str
    score: float


class KnowledgeRetriever(Protocol):
    """Contract for retrieving relevant knowledge passages."""

    def search(
        self,
        query: str,
        *,
        limit: int = 3,
    ) -> list[KnowledgeMatch]:
        """Return the most relevant passages for a query."""
        ...