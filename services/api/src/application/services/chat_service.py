"""Private chatbot application service."""

from application.ports.chat_model import ChatModel


class ChatService:
    """Generate responses through a configured LLM provider."""

    def __init__(self, chat_model: ChatModel) -> None:
        self._chat_model = chat_model

    def chat(
        self,
        *,
        model: str,
        message: str,
    ) -> str:
        """Generate a chatbot response."""

        clean_model = model.strip()
        clean_message = message.strip()

        if not clean_model:
            raise ValueError("model cannot be empty.")

        if not clean_message:
            raise ValueError("message cannot be empty.")

        return self._chat_model.generate_reply(
            model=clean_model,
            message=clean_message,
        )