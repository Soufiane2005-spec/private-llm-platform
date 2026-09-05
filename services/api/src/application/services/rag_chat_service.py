"""Retrieval-augmented chatbot application service."""

from dataclasses import dataclass

from application.ports.chat_model import ChatModel
from application.ports.knowledge_retriever import (
    KnowledgeMatch,
    KnowledgeRetriever,
)

NO_INFORMATION_REPLY = (
    "Je n’ai pas trouvé cette information dans la documentation disponible."
)


@dataclass(frozen=True)
class RagChatResult:
    """Result returned by the RAG chatbot."""

    reply: str
    sources: list[str]


class RagChatService:
    """Generate answers grounded in retrieved local documentation."""

    def __init__(
        self,
        *,
        chat_model: ChatModel,
        knowledge_retriever: KnowledgeRetriever,
    ) -> None:
        self._chat_model = chat_model
        self._knowledge_retriever = knowledge_retriever

    def chat(
        self,
        *,
        model: str,
        message: str,
    ) -> RagChatResult:
        """Retrieve context and generate a grounded answer."""

        clean_model = model.strip()
        clean_message = message.strip()

        if not clean_model:
            raise ValueError("model cannot be empty.")

        if not clean_message:
            raise ValueError("message cannot be empty.")

        matches = self._knowledge_retriever.search(
            clean_message,
            limit=3,
        )

        if not matches:
            return RagChatResult(
                reply=NO_INFORMATION_REPLY,
                sources=[],
            )

        prompt = self._build_prompt(
            question=clean_message,
            matches=matches,
        )

        reply = self._chat_model.generate_reply(
            model=clean_model,
            message=prompt,
        )

        sources = list(
            dict.fromkeys(
                match.source
                for match in matches
            )
        )

        return RagChatResult(
            reply=reply,
            sources=sources,
        )

    @staticmethod
    def _build_prompt(
        *,
        question: str,
        matches: list[KnowledgeMatch],
    ) -> str:
        context_sections: list[str] = []

        for index, match in enumerate(
            matches,
            start=1,
        ):
            context_sections.append(
                f"[Source {index}: {match.source}]\n"
                f"{match.content}"
            )

        context = "\n\n".join(context_sections)

        return (
            "Tu es un assistant privé destiné à répondre à partir "
            "d’une documentation interne.\n\n"
            "RÈGLES IMPORTANTES :\n"
            "- Réponds uniquement à partir du contexte fourni.\n"
            "- N’invente aucune procédure ou information.\n"
            "- Si le contexte ne permet pas de répondre, dis clairement "
            "que l’information n’est pas disponible.\n"
            "- Réponds en français de manière claire et concise.\n"
            "- Les documents de démonstration ne sont pas des procédures "
            "officielles.\n\n"
            f"CONTEXTE :\n{context}\n\n"
            f"QUESTION :\n{question}\n\n"
            "RÉPONSE :"
        )