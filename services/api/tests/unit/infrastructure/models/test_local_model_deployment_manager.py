"""Unit tests for the local Ollama provisioning workflow."""

from application.services.model_catalog import ModelCatalog
from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry
from infrastructure.llm.ollama_model_client import OllamaModelClientError
from infrastructure.models.local_model_deployment_manager import (
    LocalModelDeploymentManager,
)
from infrastructure.persistence.in_memory_model_catalog_repository import (
    InMemoryModelCatalogRepository,
)


class FakeOllamaRuntimeClient:
    """In-memory double for the Ollama runtime model management port."""

    def __init__(
        self,
        *,
        initial_models: tuple[str, ...] = (),
        fail_pull_with: Exception | None = None,
    ) -> None:
        self._models = set(initial_models)
        self._fail_pull_with = fail_pull_with
        self.pull_calls: list[str] = []

    def has_model(self, model: str) -> bool:
        return model in self._models or (
            ":" not in model and f"{model}:latest" in self._models
        )

    def pull_model(self, model: str) -> None:
        self.pull_calls.append(model)
        if self._fail_pull_with is not None:
            raise self._fail_pull_with
        self._models.add(model)

    def ensure_model_available(self, model: str) -> bool:
        if self.has_model(model):
            return False
        self.pull_model(model)
        return True


def _deployment(model: str, engine: LLMEngine = LLMEngine.OLLAMA) -> ModelDeployment:
    return ModelDeployment(
        deployment_id="dep-1",
        model=model,
        engine=engine,
        status=ModelDeploymentStatus.DEPLOYING,
        runtime_state="deployment-job-submitted",
    )


def _catalog_with_phi3() -> ModelCatalog:
    repository = InMemoryModelCatalogRepository()
    repository.save(
        ModelCatalogEntry(
            model_id="phi3-mini",
            display_name="Phi-3 Mini",
            engine=LLMEngine.OLLAMA,
            engine_model_id="phi3:mini",
        )
    )
    return ModelCatalog(repository=repository)


def test_deploy_pulls_absent_model_using_catalog_engine_model_id() -> None:
    """Deploy resolves the dynamic engine_model_id and pulls it when absent."""

    client = FakeOllamaRuntimeClient(initial_models=())
    manager = LocalModelDeploymentManager(
        model_catalog=_catalog_with_phi3(),
        ollama_client=client,
    )

    result = manager.deploy(_deployment("phi3-mini"))

    assert client.pull_calls == ["phi3:mini"]
    assert result.status is ModelDeploymentStatus.RUNNING
    assert result.runtime_state == "ollama-model-pulled"


def test_deploy_is_idempotent_when_model_already_present() -> None:
    """Deploy does not re-pull a model that is already present in Ollama."""

    client = FakeOllamaRuntimeClient(initial_models=("phi3:mini",))
    manager = LocalModelDeploymentManager(
        model_catalog=_catalog_with_phi3(),
        ollama_client=client,
    )

    result = manager.deploy(_deployment("phi3-mini"))

    assert client.pull_calls == []
    assert result.status is ModelDeploymentStatus.RUNNING
    assert result.runtime_state == "ollama-model-already-present"


def test_deploy_accepts_latest_runtime_tag_for_untagged_model() -> None:
    """An untagged catalog id succeeds when Ollama reports model:latest."""

    repository = InMemoryModelCatalogRepository()
    repository.save(
        ModelCatalogEntry(
            model_id="tinyllama",
            display_name="TinyLlama",
            engine=LLMEngine.OLLAMA,
            engine_model_id="tinyllama",
        )
    )
    client = FakeOllamaRuntimeClient(initial_models=("tinyllama:latest",))
    manager = LocalModelDeploymentManager(
        model_catalog=ModelCatalog(repository=repository),
        ollama_client=client,
    )

    result = manager.deploy(_deployment("tinyllama"))

    assert client.pull_calls == []
    assert result.status is ModelDeploymentStatus.RUNNING
    assert result.runtime_state == "ollama-model-already-present"


def test_deploy_works_without_catalog_using_raw_engine_tag() -> None:
    """When no catalog entry matches, the raw deployment model is used directly."""

    client = FakeOllamaRuntimeClient(initial_models=())
    manager = LocalModelDeploymentManager(ollama_client=client)

    result = manager.deploy(_deployment("qwen2.5:1.5b"))

    assert client.pull_calls == ["qwen2.5:1.5b"]
    assert result.status is ModelDeploymentStatus.RUNNING


def test_deploy_does_not_hardcode_any_specific_model() -> None:
    """The provisioning workflow works for any dynamic catalog model id."""

    repository = InMemoryModelCatalogRepository()
    repository.save(
        ModelCatalogEntry(
            model_id="mystery-model",
            display_name="Mystery Model",
            engine=LLMEngine.OLLAMA,
            engine_model_id="totally-unseen-tag:latest",
        )
    )
    catalog = ModelCatalog(repository=repository)
    client = FakeOllamaRuntimeClient(initial_models=())
    manager = LocalModelDeploymentManager(model_catalog=catalog, ollama_client=client)

    result = manager.deploy(_deployment("mystery-model"))

    assert client.pull_calls == ["totally-unseen-tag:latest"]
    assert result.status is ModelDeploymentStatus.RUNNING


def test_deploy_reports_clean_failure_when_pull_fails() -> None:
    """A pull failure fails the deployment with a useful, model-specific error."""

    client = FakeOllamaRuntimeClient(
        initial_models=(),
        fail_pull_with=OllamaModelClientError("disk full"),
    )
    manager = LocalModelDeploymentManager(
        model_catalog=_catalog_with_phi3(),
        ollama_client=client,
    )

    result = manager.deploy(_deployment("phi3-mini"))

    assert result.status is ModelDeploymentStatus.FAILED
    assert result.runtime_state == "ollama-pull-failed"
    assert "phi3:mini" in result.error
    assert "disk full" in result.error


def test_deploy_does_not_claim_success_when_model_still_missing_after_pull() -> None:
    """ensure_model_available's own post-pull verification surfaces as a failure."""

    class LyingClient(FakeOllamaRuntimeClient):
        def ensure_model_available(self, model: str) -> bool:
            self.pull_calls.append(model)
            raise OllamaModelClientError(
                f"Ollama reported completion for '{model}' but the model "
                "is still not listed by the runtime."
            )

    manager = LocalModelDeploymentManager(
        model_catalog=_catalog_with_phi3(),
        ollama_client=LyingClient(),
    )

    result = manager.deploy(_deployment("phi3-mini"))

    assert result.status is ModelDeploymentStatus.FAILED
    assert "still not listed" in result.error


def test_start_reuses_deploy_provisioning_logic() -> None:
    """Starting a stopped Ollama deployment re-provisions the model."""

    client = FakeOllamaRuntimeClient(initial_models=())
    manager = LocalModelDeploymentManager(
        model_catalog=_catalog_with_phi3(),
        ollama_client=client,
    )
    stopped = _deployment("phi3-mini").with_status(
        ModelDeploymentStatus.STOPPED, runtime_state="scaled-to-zero"
    )

    result = manager.start(stopped)

    assert client.pull_calls == ["phi3:mini"]
    assert result.status is ModelDeploymentStatus.RUNNING


def test_vllm_gpu_unavailable_behavior_is_unaffected() -> None:
    """vLLM deployments still fail cleanly without a GPU, unrelated to Ollama."""

    manager = LocalModelDeploymentManager(gpu_available=False)

    result = manager.deploy(_deployment("smollm2-135m", engine=LLMEngine.VLLM))

    assert result.status is ModelDeploymentStatus.FAILED
    assert result.runtime_state == "gpu-unavailable"
