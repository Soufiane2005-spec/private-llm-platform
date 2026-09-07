"""Infrastructure validation for generated vLLM Kubernetes deployments."""

from types import SimpleNamespace

from domain.models.deployment import ModelDeployment
from domain.models.llm_engine import LLMEngine
from infrastructure.models.kubernetes_model_deployment_manager import (
    KubernetesModelDeploymentManager,
)


class FakeAppsApi:
    """Minimal fake Kubernetes Apps API."""

    def read_namespaced_deployment_status(
        self,
        *,
        name: str,
        namespace: str,
    ) -> SimpleNamespace:
        del name
        del namespace

        return SimpleNamespace(
            spec=SimpleNamespace(replicas=1),
            status=SimpleNamespace(
                available_replicas=0,
                ready_replicas=0,
            ),
        )


class FakeCoreApi:
    """Minimal fake Kubernetes Core API."""

    def list_node(self) -> SimpleNamespace:
        return SimpleNamespace(
            items=[
                SimpleNamespace(
                    status=SimpleNamespace(
                        allocatable={
                            "nvidia.com/gpu": "1",
                        }
                    )
                )
            ]
        )


def test_vllm_kubernetes_deployment_is_gpu_and_nonroot_ready() -> None:
    manager = KubernetesModelDeploymentManager(
        namespace="llm-platform",
        apps_api=FakeAppsApi(),
        core_api=FakeCoreApi(),
    )

    deployment = ModelDeployment(
    deployment_id="test-vllm-deployment",
    model="HuggingFaceTB/SmolLM2-360M-Instruct",
    engine=LLMEngine.VLLM,
)

    body = manager._deployment_body(
        deployment,
        replicas=1,
    )

    assert body["spec"]["strategy"] == {
        "type": "Recreate",
    }

    pod_spec = body["spec"]["template"]["spec"]
    container = pod_spec["containers"][0]

    assert container["resources"]["requests"]["nvidia.com/gpu"] == "1"
    assert container["resources"]["limits"]["nvidia.com/gpu"] == "1"

    security_context = container["securityContext"]

    assert security_context["runAsNonRoot"] is True
    assert security_context["runAsUser"] == 10001
    assert security_context["runAsGroup"] == 10001
    assert security_context["allowPrivilegeEscalation"] is False

    env = {
        item["name"]: item.get("value")
        for item in container["env"]
    }

    assert env["VLLM_USE_V2_MODEL_RUNNER"] == "0"
    assert env["VLLM_WSL2_ENABLE_PIN_MEMORY"] == "1"
    assert env["HF_HOME"] == "/cache/huggingface"
    assert env["XDG_CACHE_HOME"] == "/cache"
    assert env["HOME"] == "/tmp"

    args = container["args"]

    assert "--gpu-memory-utilization" in args

    gpu_memory_index = args.index(
        "--gpu-memory-utilization"
    )

    assert args[gpu_memory_index + 1] == "0.75"

    volume_mounts = {
        item["name"]: item["mountPath"]
        for item in container["volumeMounts"]
    }

    assert volume_mounts["model-cache"] == "/cache/huggingface"
    assert volume_mounts["tmp"] == "/tmp"
    assert volume_mounts["dshm"] == "/dev/shm"

    volume_names = {
        item["name"]
        for item in pod_spec["volumes"]
    }

    assert "model-cache" in volume_names
    assert "tmp" in volume_names
    assert "dshm" in volume_names