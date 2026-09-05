"""Kubernetes model deployment manager."""

from datetime import UTC, datetime

from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine


class KubernetesModelDeploymentError(RuntimeError):
    """Raised when Kubernetes lifecycle management fails."""


class KubernetesModelDeploymentManager:
    """Manage LLM model runtimes through the Kubernetes Python client."""

    def __init__(
        self,
        *,
        namespace: str = "llm-platform",
        apps_api: object | None = None,
        core_api: object | None = None,
    ) -> None:
        if not namespace.strip():
            raise ValueError("namespace cannot be empty.")

        self._namespace = namespace

        if apps_api is None or core_api is None:
            apps_api, core_api = self._load_kubernetes_clients()

        self._apps_api = apps_api
        self._core_api = core_api

    def deploy(self, deployment: ModelDeployment) -> ModelDeployment:
        """Create or update a Kubernetes Deployment for the model."""

        if deployment.engine is LLMEngine.OLLAMA:
            self._scale(deployment, replicas=1)
            return self._status_from_kubernetes(deployment)

        if deployment.engine is LLMEngine.VLLM and not self._gpu_available():
            return deployment.with_status(
                ModelDeploymentStatus.FAILED,
                runtime_state="gpu-unavailable",
                error="vLLM deployment requires an NVIDIA GPU, but none is available.",
                gpu_available=False,
            )

        name = self._resource_name(deployment)
        body = self._deployment_body(deployment, replicas=1)

        try:
            self._apps_api.patch_namespaced_deployment(
                name=name,
                namespace=self._namespace,
                body=body,
            )
        except Exception as exc:
            if not self._is_not_found_error(exc):
                raise KubernetesModelDeploymentError(
                    "Unable to update Kubernetes model deployment."
                ) from exc

            try:
                self._apps_api.create_namespaced_deployment(
                    namespace=self._namespace,
                    body=body,
                )
            except Exception as create_exc:
                raise KubernetesModelDeploymentError(
                    "Unable to create Kubernetes model deployment."
                ) from create_exc

        return self._status_from_kubernetes(deployment)

    def start(self, deployment: ModelDeployment) -> ModelDeployment:
        """Scale a deployment to one replica."""

        self._scale(deployment, replicas=1)
        return self._status_from_kubernetes(deployment)

    def stop(self, deployment: ModelDeployment) -> ModelDeployment:
        """Scale a deployment to zero replicas."""

        self._scale(deployment, replicas=0)
        return deployment.with_status(
            ModelDeploymentStatus.STOPPED,
            runtime_state="scaled-to-zero",
            gpu_available=self._gpu_available(),
        )

    def restart(self, deployment: ModelDeployment) -> ModelDeployment:
        """Trigger a rollout restart."""

        name = self._resource_name(deployment)
        restarted_at = datetime.now(UTC).isoformat()

        try:
            self._apps_api.patch_namespaced_deployment(
                name=name,
                namespace=self._namespace,
                body={
                    "spec": {
                        "template": {
                            "metadata": {
                                "annotations": {
                                    "kubectl.kubernetes.io/restartedAt": restarted_at
                                }
                            }
                        }
                    }
                },
            )
        except Exception as exc:
            raise KubernetesModelDeploymentError(
                "Unable to restart Kubernetes model deployment."
            ) from exc

        return self._status_from_kubernetes(deployment)

    def delete(self, deployment: ModelDeployment) -> None:
        """Delete the Kubernetes Deployment for the model."""

        try:
            self._apps_api.delete_namespaced_deployment(
                name=self._resource_name(deployment),
                namespace=self._namespace,
            )
        except Exception as exc:
            raise KubernetesModelDeploymentError(
                "Unable to delete Kubernetes model deployment."
            ) from exc

    def _scale(self, deployment: ModelDeployment, *, replicas: int) -> None:
        try:
            self._apps_api.patch_namespaced_deployment_scale(
                name=self._resource_name(deployment),
                namespace=self._namespace,
                body={"spec": {"replicas": replicas}},
            )
        except Exception as exc:
            raise KubernetesModelDeploymentError(
                "Unable to scale Kubernetes model deployment."
            ) from exc

    def _status_from_kubernetes(self, deployment: ModelDeployment) -> ModelDeployment:
        try:
            runtime = self._apps_api.read_namespaced_deployment_status(
                name=self._resource_name(deployment),
                namespace=self._namespace,
            )
        except Exception as exc:
            raise KubernetesModelDeploymentError(
                "Unable to read Kubernetes model deployment status."
            ) from exc

        desired = runtime.spec.replicas or 0
        available = runtime.status.available_replicas or 0
        ready = runtime.status.ready_replicas or 0

        if desired == 0:
            status = ModelDeploymentStatus.STOPPED
            state = "scaled-to-zero"
        elif available > 0 and ready > 0:
            status = ModelDeploymentStatus.RUNNING
            state = f"ready:{ready}/{desired}"
        else:
            status = ModelDeploymentStatus.LOADING
            state = f"ready:{ready}/{desired}"

        return deployment.with_status(
            status,
            runtime_state=state,
            gpu_available=self._gpu_available(),
        )

    def _gpu_available(self) -> bool:
        try:
            nodes = self._core_api.list_node().items
        except Exception:
            return False

        for node in nodes:
            allocatable = getattr(node.status, "allocatable", {}) or {}
            value = allocatable.get("nvidia.com/gpu")

            try:
                if value and int(value) > 0:
                    return True
            except (TypeError, ValueError):
                continue

        return False

    def _deployment_body(self, deployment: ModelDeployment, *, replicas: int) -> dict:
        name = self._resource_name(deployment)
        container = self._container(deployment)

        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": name,
                "namespace": self._namespace,
                "labels": {
                    "app": name,
                    "managed-by": "private-llm-platform",
                },
            },
            "spec": {
                "replicas": replicas,
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {
                        "securityContext": {
                            "runAsNonRoot": True,
                            "runAsUser": 10001,
                            "runAsGroup": 10001,
                            "fsGroup": 10001,
                            "seccompProfile": {"type": "RuntimeDefault"},
                        },
                        "containers": [container],
                    },
                },
            },
        }

    def _container(self, deployment: ModelDeployment) -> dict:
        if deployment.engine is LLMEngine.OLLAMA:
            return {
                "name": "ollama",
                "image": "ollama/ollama:0.32.14",
                "ports": [{"containerPort": 11434}],
                "env": [
                    {"name": "OLLAMA_HOST", "value": "0.0.0.0:11434"},
                    {"name": "OLLAMA_MODEL", "value": deployment.model},
                ],
                "securityContext": self._container_security_context(),
                "resources": {
                    "requests": {"cpu": "500m", "memory": "1Gi"},
                    "limits": {"cpu": "4", "memory": "6Gi"},
                },
            }

        return {
            "name": "vllm",
            "image": "vllm/vllm-openai:v0.27.0",
            "ports": [{"containerPort": 8000}],
            "args": [
                "--model",
                deployment.model,
                "--served-model-name",
                deployment.model.split("/")[-1].lower(),
                "--dtype",
                "half",
            ],
            "securityContext": self._container_security_context(),
            "resources": {
                "requests": {"cpu": "1", "memory": "2Gi", "nvidia.com/gpu": "1"},
                "limits": {"cpu": "6", "memory": "8Gi", "nvidia.com/gpu": "1"},
            },
        }

    @staticmethod
    def _container_security_context() -> dict:
        return {
            "allowPrivilegeEscalation": False,
            "runAsNonRoot": True,
            "runAsUser": 10001,
            "runAsGroup": 10001,
            "readOnlyRootFilesystem": False,
            "capabilities": {"drop": ["ALL"]},
        }

    @staticmethod
    def _resource_name(deployment: ModelDeployment) -> str:
        if deployment.engine is LLMEngine.OLLAMA:
            return "ollama"

        clean_model = (
            deployment.model.lower()
            .replace("/", "-")
            .replace(":", "-")
            .replace("_", "-")
            .replace(".", "-")
        )
        return f"model-{deployment.engine.value}-{clean_model}"[:63].rstrip("-")

    @staticmethod
    def _is_not_found_error(exc: Exception) -> bool:
        return getattr(exc, "status", None) == 404

    @staticmethod
    def _load_kubernetes_clients() -> tuple[object, object]:
        try:
            from kubernetes import client, config
        except ImportError as exc:
            raise KubernetesModelDeploymentError(
                "The kubernetes Python package is required for Kubernetes model management."
            ) from exc

        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()

        return client.AppsV1Api(), client.CoreV1Api()
