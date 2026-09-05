"""Tests for Kubernetes-backed model deployment management."""

from types import SimpleNamespace

from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine
from infrastructure.models.kubernetes_model_deployment_manager import (
    KubernetesModelDeploymentManager,
)


class NotFoundError(Exception):
    """Minimal Kubernetes-like not found error."""

    status = 404


class FakeAppsApi:
    """Small fake for the Kubernetes AppsV1Api surface used by the manager."""

    def __init__(self, *, exists: bool = True, ready: int = 1, desired: int = 1) -> None:
        self.exists = exists
        self.ready = ready
        self.desired = desired
        self.created: list[dict] = []
        self.patches: list[dict] = []
        self.scales: list[dict] = []
        self.deleted: list[str] = []

    def patch_namespaced_deployment(
        self,
        *,
        name: str,
        namespace: str,
        body: dict,
    ) -> None:
        if not self.exists:
            raise NotFoundError

        self.patches.append({"name": name, "namespace": namespace, "body": body})

    def create_namespaced_deployment(self, *, namespace: str, body: dict) -> None:
        self.exists = True
        self.created.append({"namespace": namespace, "body": body})

    def patch_namespaced_deployment_scale(
        self,
        *,
        name: str,
        namespace: str,
        body: dict,
    ) -> None:
        self.desired = body["spec"]["replicas"]
        self.ready = 0 if self.desired == 0 else self.ready
        self.scales.append({"name": name, "namespace": namespace, "body": body})

    def read_namespaced_deployment_status(
        self,
        *,
        name: str,
        namespace: str,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            metadata=SimpleNamespace(name=name, namespace=namespace),
            spec=SimpleNamespace(replicas=self.desired),
            status=SimpleNamespace(
                available_replicas=self.ready,
                ready_replicas=self.ready,
            ),
        )

    def delete_namespaced_deployment(self, *, name: str, namespace: str) -> None:
        self.deleted.append(f"{namespace}/{name}")


class FakeCoreApi:
    """Small fake for node capacity lookups."""

    def __init__(self, gpu: str | None = None) -> None:
        self.gpu = gpu

    def list_node(self) -> SimpleNamespace:
        allocatable = {}

        if self.gpu is not None:
            allocatable["nvidia.com/gpu"] = self.gpu

        return SimpleNamespace(
            items=[
                SimpleNamespace(
                    status=SimpleNamespace(allocatable=allocatable),
                )
            ]
        )


def deployment(engine: LLMEngine = LLMEngine.OLLAMA) -> ModelDeployment:
    """Return a valid deployment fixture."""

    model = "qwen2.5:1.5b" if engine is LLMEngine.OLLAMA else "Qwen/Qwen3-0.6B"
    return ModelDeployment(
        deployment_id="deployment-1",
        model=model,
        engine=engine,
    )


def test_deploy_ollama_scales_existing_runtime() -> None:
    """Ollama deployments use the existing service-backed runtime."""

    apps_api = FakeAppsApi(exists=True, ready=1, desired=1)
    manager = KubernetesModelDeploymentManager(
        namespace="llm-platform",
        apps_api=apps_api,
        core_api=FakeCoreApi(),
    )

    result = manager.deploy(deployment())

    assert apps_api.created == []
    assert apps_api.scales == [
        {
            "name": "ollama",
            "namespace": "llm-platform",
            "body": {"spec": {"replicas": 1}},
        }
    ]
    assert result.status is ModelDeploymentStatus.RUNNING
    assert result.runtime_state == "ready:1/1"


def test_deploy_vllm_without_gpu_fails_before_kubernetes_mutation() -> None:
    """vLLM deployments fail explicitly when no NVIDIA GPU is allocatable."""

    apps_api = FakeAppsApi(exists=True)
    manager = KubernetesModelDeploymentManager(
        apps_api=apps_api,
        core_api=FakeCoreApi(gpu="0"),
    )

    result = manager.deploy(deployment(LLMEngine.VLLM))

    assert result.status is ModelDeploymentStatus.FAILED
    assert result.runtime_state == "gpu-unavailable"
    assert result.gpu_available is False
    assert "requires an NVIDIA GPU" in (result.error or "")
    assert apps_api.patches == []
    assert apps_api.created == []


def test_deploy_vllm_with_gpu_requests_gpu_resources() -> None:
    """vLLM deployments request and limit one NVIDIA GPU."""

    apps_api = FakeAppsApi(exists=True, ready=0, desired=1)
    manager = KubernetesModelDeploymentManager(
        apps_api=apps_api,
        core_api=FakeCoreApi(gpu="1"),
    )

    result = manager.deploy(deployment(LLMEngine.VLLM))

    container = apps_api.patches[0]["body"]["spec"]["template"]["spec"]["containers"][0]
    assert container["resources"]["requests"]["nvidia.com/gpu"] == "1"
    assert container["resources"]["limits"]["nvidia.com/gpu"] == "1"
    assert result.status is ModelDeploymentStatus.LOADING
    assert result.runtime_state == "ready:0/1"
    assert result.gpu_available is True


def test_stop_scales_deployment_to_zero() -> None:
    """Stopping a deployment scales it to zero and reports stopped."""

    apps_api = FakeAppsApi(exists=True, ready=1, desired=1)
    manager = KubernetesModelDeploymentManager(
        apps_api=apps_api,
        core_api=FakeCoreApi(gpu="not-a-number"),
    )

    result = manager.stop(deployment())

    assert apps_api.scales[0]["body"] == {"spec": {"replicas": 0}}
    assert result.status is ModelDeploymentStatus.STOPPED
    assert result.runtime_state == "scaled-to-zero"
    assert result.gpu_available is False


def test_restart_patches_rollout_annotation() -> None:
    """Restarting patches the pod template with a rollout timestamp."""

    apps_api = FakeAppsApi(exists=True, ready=1, desired=1)
    manager = KubernetesModelDeploymentManager(
        apps_api=apps_api,
        core_api=FakeCoreApi(),
    )

    result = manager.restart(deployment())

    annotations = apps_api.patches[0]["body"]["spec"]["template"]["metadata"][
        "annotations"
    ]
    assert "kubectl.kubernetes.io/restartedAt" in annotations
    assert result.status is ModelDeploymentStatus.RUNNING
