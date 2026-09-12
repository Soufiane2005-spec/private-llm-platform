"""Retrieval-augmented chatbot application service."""

from dataclasses import dataclass

from application.ports.chat_model import ChatModel
from application.ports.knowledge_retriever import (
    KnowledgeMatch,
    KnowledgeRetriever,
)
from application.services.model_catalog import (
    ModelCatalog,
    ModelNotFoundError,
)
from application.services.model_runtime_availability import (
    ModelRuntimeAvailability,
)
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry


NO_INFORMATION_REPLY = (
    "Je n'ai pas trouvé cette information "
    "dans la documentation disponible."
)


@dataclass(frozen=True)
class RagChatResult:
    """Result returned by the RAG chatbot."""

    reply: str
    sources: list[KnowledgeMatch]
    model: str


class RagChatService:
    """Generate answers grounded in retrieved local documentation."""

    def __init__(
        self,
        *,
        chat_model: ChatModel,
        knowledge_retriever: KnowledgeRetriever,
        model_catalog: ModelCatalog | None = None,
        runtime_availability: ModelRuntimeAvailability | None = None,
    ) -> None:
        self._chat_model = chat_model
        self._knowledge_retriever = knowledge_retriever
        self._model_catalog = model_catalog
        self._runtime_availability = runtime_availability

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

        catalog_model = self._resolve_model(clean_model)

        runtime_model = (
            catalog_model.engine_model_id
            if catalog_model
            else clean_model
        )

        matches = self._knowledge_retriever.search(
            clean_message,
            limit=3,
        )

        if not matches:
            return RagChatResult(
                reply=NO_INFORMATION_REPLY,
                sources=[],
                model=runtime_model,
            )

        prompt = self._build_prompt(
            question=clean_message,
            matches=matches,
        )

        reply = self._chat_model.generate_reply(
            model=runtime_model,
            message=prompt,
        )

        return RagChatResult(
            reply=reply,
            sources=matches,
            model=runtime_model,
        )

    def _resolve_model(
        self,
        model: str,
    ) -> ModelCatalogEntry | None:
        if self._model_catalog is None:
            return None

        catalog_model = self._find_catalog_model(model)

        if catalog_model.engine is not LLMEngine.OLLAMA:
            raise ValueError(
                "Chat generation is not configured for "
                f"{catalog_model.engine.value}."
            )

        if not catalog_model.enabled:
            raise ValueError(
                f"Model '{catalog_model.model_id}' is disabled."
            )

        if self._runtime_availability is not None:
            state = self._runtime_availability.state_for(
                catalog_model
            )

            if not state.runtime_available:
                detail = (
                    state.reason
                    or "runtime is unavailable"
                )

                raise ValueError(
                    f"Model '{catalog_model.model_id}' "
                    "is not runtime available: "
                    f"{detail}."
                )

        return catalog_model

    def _find_catalog_model(
        self,
        model: str,
    ) -> ModelCatalogEntry:
        assert self._model_catalog is not None

        for entry in self._model_catalog.list_models():
            identifiers = {
                entry.model_id,
                entry.engine_model_id,
                entry.benchmark_model_id,
            }

            if model in identifiers:
                return entry

        try:
            return self._model_catalog.get(model)

        except ModelNotFoundError as exc:
            raise ValueError(
                f"Model '{model}' was not found in the catalog."
            ) from exc

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
            location = (
                f"{match.source}, page {match.page}"
                if match.page is not None
                else match.source
            )

            context_sections.append(
                f"Source {index} - {location}\n"
                f"{match.content[:900]}"
            )

        context = "\n\n".join(context_sections)

        return (
            "CONTEXTE DOCUMENTAIRE\n"
            "---------------------\n"
            f"{context}\n\n"
            "QUESTION\n"
            "--------\n"
            f"{question}\n\n"
            "INSTRUCTION\n"
            "-----------\n"
            "Donne uniquement une réponse finale courte, "
            "claire et professionnelle en français. "
            "Ne reproduis pas le contexte ni les instructions."
        )