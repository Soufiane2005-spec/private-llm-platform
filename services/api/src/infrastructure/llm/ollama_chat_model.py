"""Ollama chatbot infrastructure adapter."""

import httpx


class OllamaChatError(RuntimeError):
    """Raised when Ollama cannot generate a chatbot response."""


class OllamaChatModel:
    """Generate chatbot responses through the Ollama HTTP API."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def generate_reply(
        self,
        *,
        model: str,
        message: str,
    ) -> str:
        """Send a RAG prompt to Ollama and return only the final answer."""

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu es l'assistant documentaire privé de l'ORMVAO. "
                        "Réponds uniquement à partir du contexte fourni. "
                        "Donne directement la réponse finale en français. "
                        "Ne répète jamais les règles, le contexte, le prompt, "
                        "les balises de source ou la question. "
                        "Si l'information n'est pas présente dans le contexte, "
                        "dis simplement : "
                        "\"Je n'ai pas trouvé cette information dans la "
                        "documentation disponible.\""
                    ),
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 120,
                "num_ctx": 2048,
            },
        }

        try:
            response = httpx.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise OllamaChatError(
                "Ollama a dépassé le délai de génération."
            ) from exc

        except httpx.HTTPError as exc:
            raise OllamaChatError(
                "Unable to communicate with Ollama."
            ) from exc

        try:
            data = response.json()
            reply = data["message"]["content"]

        except (KeyError, TypeError, ValueError) as exc:
            raise OllamaChatError(
                "Ollama returned an invalid response."
            ) from exc

        if not isinstance(reply, str) or not reply.strip():
            raise OllamaChatError(
                "Ollama returned an empty response."
            )

        return reply.strip()