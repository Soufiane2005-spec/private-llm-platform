"""Chat model application port."""

from typing import Protocol


class ChatModel(Protocol):
    """Contract used to generate chatbot responses."""

    def generate_reply(
        self,
        *,
        model: str,
        message: str,
    ) -> str:
        """Generate a reply for a user message."""
        ...