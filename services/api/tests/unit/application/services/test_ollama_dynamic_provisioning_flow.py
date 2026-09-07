"""End-to-end style test of Add Model -> Deploy -> Benchmark eligibility.

This exercises the real collaborators (model catalog, deployment service,
local deployment manager, and the Ollama benchmark executor) with only the
external Ollama HTTP boundary faked, to validate the dynamic Ollama model
provisioning workflow without hardcoding any specific model.
"""

import httpx
import pytest

from application.services.job_service import JobService
from application.services.model_catalog import ModelCatalog
from application.services.model_deployment_service import ModelDeploymentService
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry
from infrastructure.llm.ollama_benchmark_executor import (
    OllamaBenchmarkError,
    OllamaBenchmarkExecutor,
)
from infrastructure.models.local_model_deployment_manager import (
    LocalModelDeploymentManager,
)
from infrastructure.persistence.in_memory_job_repository import InMemoryJobRepository
from infrastructure.persistence.in_memory_model_catalog_repository import (
    InMemoryModelCatalogRepository,
)
from infrastructure.persistence.in_memory_model_deployment_repository import (
    InMemoryModelDeploymentRepository,
)
from infrastructure.queue.in_memory_job_queue import InMemoryJobQueue


class FakeOllamaServer:
    """A tiny fake Ollama HTTP server backing /api/tags, /api/pull, /api/generate."""

    def __init__(self, *, initial_models: tuple[str, ...] = ()) -> None:
        self.models: set[str] = set(initial_models)
        self.pull_calls: list[str] = []

    def tags_response(self) -> httpx.Response:
        return httpx.Response(
            200,
            json={"models": [{"name": name} for name in sorted(self.models)]},
            request=httpx.Request("GET", "http://ollama:11434/api/tags"),
        )

    def pull(self, model: str) -> "FakePullStream":
        self.pull_calls.append(model)
        self.models.add(model if ":" in model else f"{model}:latest")
        return FakePullStream([{"status": "success"}])

    def generate(self) -> "FakeGenerateStream":
        return FakeGenerateStream()


class FakePullStream:
    def __init__(self, events: list[dict]) -> None:
        self._events = events

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        import json

        return iter(json.dumps(event) for event in self._events)


class FakeGenerateStream:
    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        import json

        return iter(
            [
                json.dumps({"response": "hi"}),
                json.dumps(
                    {
                        "done": True,
                        "eval_count": 1,
                        "eval_duration": 1_000_000,
                    }
                ),
            ]
        )


@pytest.fixture
def phi3_catalog_entry() -> ModelCatalogEntry:
    return ModelCatalogEntry(
        model_id="phi3-mini",
        display_name="Phi-3 Mini",
        engine=LLMEngine.OLLAMA,
        engine_model_id="phi3:mini",
    )


def test_full_add_deploy_provision_benchmark_flow(
    monkeypatch, phi3_catalog_entry
) -> None:
    """Add Model -> Deploy -> Runtime Available -> Benchmark, end to end."""

    server = FakeOllamaServer(initial_models=("qwen2.5:1.5b",))

    def fake_get(url, *args, **kwargs):
        assert "/api/tags" in url
        return server.tags_response()

    def fake_stream(method, url, *args, **kwargs):
        if "/api/pull" in url:
            model = kwargs["json"]["model"]
            return server.pull(model)
        return server.generate()

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.get", fake_get
    )
    monkeypatch.setattr(
        "infrastructure.llm.ollama_benchmark_executor.httpx.get", fake_get
    )
    monkeypatch.setattr(
        "infrastructure.llm.ollama_benchmark_executor.httpx.stream", fake_stream
    )

    # 1. Add Model: catalog metadata only, no provisioning happens.
    catalog_repository = InMemoryModelCatalogRepository()
    catalog = ModelCatalog(repository=catalog_repository)
    catalog.add(phi3_catalog_entry)

    assert "phi3:mini" not in server.models
    assert server.pull_calls == []

    # 2. Runtime available = false before deploy.
    executor = OllamaBenchmarkExecutor()
    with pytest.raises(OllamaBenchmarkError, match="Model not available"):
        executor.execute(model="phi3:mini", prompt="hello")

    # 3. Deploy triggers a pull for the dynamic model id.
    job_repository = InMemoryJobRepository()
    job_service = JobService(queue=InMemoryJobQueue(), repository=job_repository)
    deployment_service = ModelDeploymentService(
        deployments=InMemoryModelDeploymentRepository(),
        manager=LocalModelDeploymentManager(model_catalog=catalog),
        jobs=job_service,
        job_repository=job_repository,
        model_catalog=catalog,
    )

    deployment, job = deployment_service.deploy(model="phi3-mini", engine=LLMEngine.OLLAMA)
    completed_job = deployment_service.execute_deploy(deployment.deployment_id, job.job_id)

    # 4. Pull succeeded and the deployment reports success.
    assert server.pull_calls == ["phi3:mini"]
    assert completed_job.status.value == "completed"
    final_deployment = deployment_service.get_deployment(deployment.deployment_id)
    assert final_deployment.status.value == "running"
    assert final_deployment.runtime_state == "ollama-model-pulled"

    # 5. Ollama runtime now lists the model -> runtime available = true.
    assert "phi3:mini" in server.models

    # 6. Benchmark now succeeds because the model is actually present.
    execution = executor.execute(model="phi3:mini", prompt="hello")
    assert execution.tokens_generated >= 1

    # 7. Re-deploying is idempotent: no duplicate pull.
    deployment2, job2 = deployment_service.deploy(model="phi3-mini", engine=LLMEngine.OLLAMA)
    deployment_service.execute_deploy(deployment2.deployment_id, job2.job_id)
    assert server.pull_calls == ["phi3:mini"]


def test_pull_failure_keeps_model_unavailable_for_benchmark(
    monkeypatch, phi3_catalog_entry
) -> None:
    """A failed pull leaves the deployment failed and the model ineligible."""

    server = FakeOllamaServer(initial_models=())

    def fake_get(url, *args, **kwargs):
        return server.tags_response()

    def fake_stream(method, url, *args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.get", fake_get
    )
    monkeypatch.setattr(
        "infrastructure.llm.ollama_model_client.httpx.stream", fake_stream
    )

    catalog_repository = InMemoryModelCatalogRepository()
    catalog = ModelCatalog(repository=catalog_repository)
    catalog.add(phi3_catalog_entry)

    job_repository = InMemoryJobRepository()
    job_service = JobService(queue=InMemoryJobQueue(), repository=job_repository)
    deployment_service = ModelDeploymentService(
        deployments=InMemoryModelDeploymentRepository(),
        manager=LocalModelDeploymentManager(model_catalog=catalog),
        jobs=job_service,
        job_repository=job_repository,
        model_catalog=catalog,
    )

    deployment, job = deployment_service.deploy(model="phi3-mini", engine=LLMEngine.OLLAMA)
    deployment_service.execute_deploy(deployment.deployment_id, job.job_id)

    final_deployment = deployment_service.get_deployment(deployment.deployment_id)
    assert final_deployment.status.value == "failed"
    assert final_deployment.runtime_state == "ollama-pull-failed"
    assert "phi3:mini" in final_deployment.error
    assert "phi3:mini" not in server.models
