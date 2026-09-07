"""Local deterministic model deployment manager.

This adapter is intentionally conservative: it exposes real lifecycle state
without claiming resources exist when they do not. For Ollama models this
means Deploy actually provisions the model into the configured Ollama
runtime (pulling it if absent) instead of assuming success.
"""

from application.ports.ollama_runtime_client import OllamaRuntimeClient
from application.services.model_catalog import ModelCatalog
from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine
from infrastructure.config import get_settings
from infrastructure.llm.ollama_model_client import OllamaModelClient


class LocalModelDeploymentManager:
    """Manage deployments for local/stage environments."""

    def __init__(
        self,
        *,
        gpu_available: bool = False,
        model_catalog: ModelCatalog | None = None,
        ollama_client: OllamaRuntimeClient | None = None,
    ) -> None:
        self._gpu_available = gpu_available
        self._model_catalog = model_catalog
        self._ollama_client = ollama_client

    def deploy(self, deployment: ModelDeployment) -> ModelDeployment:
        """Create or update a local deployment record."""

        if deployment.engine is LLMEngine.VLLM and not self._gpu_available:
            return deployment.with_status(
                ModelDeploymentStatus.FAILED,
                runtime_state="gpu-unavailable",
                error="vLLM deployment requires an NVIDIA GPU, but none is available.",
                gpu_available=False,
            )

        if deployment.engine is LLMEngine.OLLAMA:
            return self._deploy_ollama(deployment)

        return deployment.with_status(
            ModelDeploymentStatus.RUNNING,
            runtime_state="local-runtime-ready",
            gpu_available=self._gpu_available,
        )

    def start(self, deployment: ModelDeployment) -> ModelDeployment:
        """Start a local deployment."""

        return self.deploy(deployment)

    def stop(self, deployment: ModelDeployment) -> ModelDeployment:
        """Stop a local deployment."""

        return deployment.with_status(
            ModelDeploymentStatus.STOPPED,
            runtime_state="scaled-to-zero",
            gpu_available=self._gpu_available,
        )

    def restart(self, deployment: ModelDeployment) -> ModelDeployment:
        """Restart a local deployment."""

        stopped = self.stop(deployment)
        return self.start(stopped)

    def status(self, deployment: ModelDeployment) -> ModelDeployment:
        """Return the stored local runtime status."""

        return deployment

    def delete(self, deployment: ModelDeployment) -> None:
        """No-op for local deployments."""

    def _deploy_ollama(self, deployment: ModelDeployment) -> ModelDeployment:
        engine_model_id = self._resolve_engine_model_id(deployment)
        client = self._resolve_ollama_client()

        try:
            pulled = client.ensure_model_available(engine_model_id)
        except Exception as exc:  # noqa: BLE001 - surfaced as a failed deployment
            return deployment.with_status(
                ModelDeploymentStatus.FAILED,
                runtime_state="ollama-pull-failed",
                error=(
                    f"Unable to provision Ollama model '{engine_model_id}': "
                    f"{exc}"
                ),
                gpu_available=self._gpu_available,
            )

        runtime_state = (
            "ollama-model-pulled" if pulled else "ollama-model-already-present"
        )
        return deployment.with_status(
            ModelDeploymentStatus.RUNNING,
            runtime_state=runtime_state,
            gpu_available=self._gpu_available,
        )

    def _resolve_engine_model_id(self, deployment: ModelDeployment) -> str:
        """Resolve the dynamic Ollama tag to provision for this deployment.

        ``deployment.model`` may be a catalog platform id (e.g.
        ``phi3-mini``) or already be the raw Ollama tag (e.g.
        ``phi3:mini``), depending on how the deployment was created. The
        catalog, when available, is authoritative.
        """

        if self._model_catalog is not None:
            for entry in self._model_catalog.list_models():
                if entry.engine is not deployment.engine:
                    continue

                identifiers = {
                    entry.model_id,
                    entry.engine_model_id,
                    entry.benchmark_model_id,
                }
                if deployment.model in identifiers:
                    return entry.engine_model_id

        return deployment.model

    def _resolve_ollama_client(self) -> OllamaRuntimeClient:
        if self._ollama_client is not None:
            return self._ollama_client

        settings = get_settings()
        self._ollama_client = OllamaModelClient(
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_timeout_seconds,
        )
        return self._ollama_client
