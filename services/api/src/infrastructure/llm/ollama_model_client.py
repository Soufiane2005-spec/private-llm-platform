"""HTTP adapter for provisioning models inside an Ollama runtime."""

import json

import httpx

from application.services.ollama_model_names import ollama_models_match


class OllamaModelClientError(RuntimeError):
    """Raised when the Ollama HTTP API cannot list or pull a model."""


class OllamaModelClient:
    """Manage models available to an Ollama runtime through its HTTP API.

    This client only handles runtime model *management* (listing which
    models are present, and pulling new ones). Chat generation and
    benchmark execution have their own adapters.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 120.0,
        pull_timeout_seconds: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        # Pulling a model can take far longer than a status check, so give
        # it a generous floor unless the caller overrides it explicitly.
        self._pull_timeout_seconds = (
            pull_timeout_seconds
            if pull_timeout_seconds is not None
            else max(timeout_seconds, 900.0)
        )

    def list_model_names(self) -> set[str]:
        """Return the set of model tags currently available in Ollama."""

        try:
            response = httpx.get(
                f"{self._base_url}/api/tags",
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            detail = self._response_detail(exc.response)
            raise OllamaModelClientError(
                f"Unable to list Ollama models: HTTP "
                f"{exc.response.status_code}: {detail}"
            ) from exc
        except (httpx.RequestError, ValueError) as exc:
            raise OllamaModelClientError(
                f"Unable to reach Ollama at {self._base_url}: {exc}"
            ) from exc

        return {
            item.get("name")
            for item in body.get("models", [])
            if isinstance(item, dict) and item.get("name")
        }

    def has_model(self, model: str) -> bool:
        """Return whether the given model tag is present in Ollama."""

        return any(
            ollama_models_match(model, runtime_name)
            for runtime_name in self.list_model_names()
        )

    def pull_model(self, model: str) -> None:
        """Pull (download) a model into the configured Ollama runtime."""

        payload = {"model": model, "stream": True}

        try:
            with httpx.stream(
                "POST",
                f"{self._base_url}/api/pull",
                json=payload,
                timeout=self._pull_timeout_seconds,
            ) as response:
                response.raise_for_status()

                status_seen = False
                for line in response.iter_lines():
                    if not line:
                        continue

                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue

                    if not isinstance(event, dict):
                        continue

                    if event.get("error"):
                        raise OllamaModelClientError(
                            f"Ollama failed to pull model '{model}': "
                            f"{event['error']}"
                        )

                    if event.get("status"):
                        status_seen = True
        except httpx.HTTPStatusError as exc:
            detail = self._response_detail(exc.response)
            raise OllamaModelClientError(
                f"Ollama pull request for '{model}' failed with HTTP "
                f"{exc.response.status_code}: {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaModelClientError(
                f"Unable to reach Ollama at {self._base_url} to pull "
                f"'{model}': {exc}"
            ) from exc

        if not status_seen:
            raise OllamaModelClientError(
                f"Ollama did not report any progress while pulling '{model}'."
            )

    def ensure_model_available(self, model: str) -> bool:
        """Ensure a model tag is present in Ollama, pulling it if absent.

        Returns ``True`` when a pull was performed and ``False`` when the
        model was already present, so callers can keep Deploy idempotent.
        """

        if self.has_model(model):
            return False

        self.pull_model(model)

        if not self.has_model(model):
            raise OllamaModelClientError(
                f"Ollama reported completion for '{model}' but the model "
                "is still not listed by the runtime."
            )

        return True

    @staticmethod
    def _response_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text[:300]

        if isinstance(body, dict):
            error = body.get("error")
            if error:
                return str(error)

        return str(body)[:300]
