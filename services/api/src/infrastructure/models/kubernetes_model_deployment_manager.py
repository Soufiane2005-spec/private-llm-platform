"""Kubernetes model deployment manager."""

import re
from datetime import UTC, datetime

from application.services.model_catalog import ModelCatalog, ModelNotFoundError
from domain.models.deployment import ModelDeployment, ModelDeploymentStatus
from domain.models.llm_engine import LLMEngine
from domain.models.model_catalog import ModelCatalogEntry


class KubernetesModelDeploymentError(RuntimeError):
    """Raised when Kubernetes lifecycle management fails."""


class KubernetesModelDeploymentManager:
    """Manage LLM model runtimes through the Kubernetes Python client."""

    def __init__(
        self,
        *,
        namespace: str = "llm-platform",
        context: str | None = None,
        model_catalog: ModelCatalog | None = None,
        apps_api: object | None = None,
        core_api: object | None = None,
    ) -> None:
        if not namespace.strip():
            raise ValueError("namespace cannot be empty.")

        self._namespace = namespace
        self._context = context.strip() if context else None
        self._model_catalog = model_catalog

        if apps_api is None or core_api is None:
            apps_api, core_api = self._load_kubernetes_clients(context=self._context)

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

        self._upsert_service(deployment)
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
        """Delete Kubernetes resources for the model.

        Deletion is idempotent: resources that are already absent are treated
        as successfully deleted.
        """

        try:
            self._apps_api.delete_namespaced_deployment(
                name=self._resource_name(deployment),
                namespace=self._namespace,
            )
        except Exception as exc:
            if not self._is_not_found_error(exc):
                raise KubernetesModelDeploymentError(
                    "Unable to delete Kubernetes model deployment."
                ) from exc

        if deployment.engine is LLMEngine.VLLM:
            try:
                self._core_api.delete_namespaced_service(
                    name=self._resource_name(deployment),
                    namespace=self._namespace,
                )
            except Exception as exc:
                if not self._is_not_found_error(exc):
                    raise KubernetesModelDeploymentError(
                        "Unable to delete Kubernetes model service."
                    ) from exc

    def status(self, deployment: ModelDeployment) -> ModelDeployment:
        """Return current Kubernetes status for a deployment."""

        return self._status_from_kubernetes(deployment)

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

    def _deployment_body(
        self,
        deployment: ModelDeployment,
        *,
        replicas: int,
    ) -> dict:
        name = self._resource_name(deployment)
        container = self._container(deployment)

        pod_spec: dict = {
            "securityContext": {
                "runAsNonRoot": True,
                "runAsUser": 10001,
                "runAsGroup": 10001,
                "fsGroup": 10001,
                "seccompProfile": {"type": "RuntimeDefault"},
            },
            "containers": [container],
        }

        if deployment.engine is LLMEngine.VLLM:
            pod_spec["volumes"] = [
                {
                    "name": "dshm",
                    "emptyDir": {
                        "medium": "Memory",
                        "sizeLimit": "2Gi",
                    },
                },
                {
                    "name": "model-cache",
                    "emptyDir": {},
                },
                {
                    "name": "tmp",
                    "emptyDir": {},
                },
            ]

        deployment_spec: dict = {
            "replicas": replicas,
            "selector": {
                "matchLabels": {
                    "app": name,
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": name,
                    }
                },
                "spec": pod_spec,
            },
        }

        if deployment.engine is LLMEngine.VLLM:
            deployment_spec["strategy"] = {
                "type": "Recreate",
            }

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
            "spec": deployment_spec,
        }

    def _container(self, deployment: ModelDeployment) -> dict:
        if deployment.engine is LLMEngine.OLLAMA:
            return {
                "name": "ollama",
                "image": "ollama/ollama:0.32.14",
                "ports": [
                    {
                        "containerPort": 11434,
                    }
                ],
                "env": [
                    {
                        "name": "OLLAMA_HOST",
                        "value": "0.0.0.0:11434",
                    },
                    {
                        "name": "OLLAMA_MODEL",
                        "value": deployment.model,
                    },
                ],
                "securityContext": self._container_security_context(),
                "resources": {
                    "requests": {
                        "cpu": "500m",
                        "memory": "1Gi",
                    },
                    "limits": {
                        "cpu": "4",
                        "memory": "6Gi",
                    },
                },
            }

        catalog_entry = self._require_catalog_entry(deployment)
        context_length = str(catalog_entry.context_length or 1024)

        return {
            "name": "vllm",
            "image": "vllm/vllm-openai:v0.27.0",
            "ports": [
                {
                    "containerPort": 8000,
                }
            ],
            "env": [
                {
                    "name": "HF_TOKEN",
                    "value": "",
                },
                {
                    "name": "VLLM_LOGGING_LEVEL",
                    "value": "INFO",
                },
                {
                    "name": "VLLM_USE_V2_MODEL_RUNNER",
                    "value": "0",
                },
                {
                    "name": "VLLM_WSL2_ENABLE_PIN_MEMORY",
                    "value": "1",
                },
                {
                    "name": "HF_HOME",
                    "value": "/cache/huggingface",
                },
                {
                    "name": "XDG_CACHE_HOME",
                    "value": "/cache",
                },
                {
                    "name": "HOME",
                    "value": "/tmp",
                },
            ],
            "args": [
                "--model",
                catalog_entry.engine_model_id,
                "--served-model-name",
                catalog_entry.served_model_name,
                "--dtype",
                "half",
                "--max-model-len",
                context_length,
                "--max-num-seqs",
                "1",
                "--gpu-memory-utilization",
                "0.75",
                "--enforce-eager",
            ],
            "startupProbe": {
                "httpGet": {
                    "path": "/health",
                    "port": 8000,
                },
                "periodSeconds": 10,
                "timeoutSeconds": 5,
                "failureThreshold": 90,
            },
            "readinessProbe": {
                "httpGet": {
                    "path": "/health",
                    "port": 8000,
                },
                "periodSeconds": 10,
                "timeoutSeconds": 5,
                "failureThreshold": 6,
            },
            "livenessProbe": {
                "httpGet": {
                    "path": "/health",
                    "port": 8000,
                },
                "periodSeconds": 30,
                "timeoutSeconds": 5,
                "failureThreshold": 3,
            },
            "securityContext": self._container_security_context(),
            "resources": {
                "requests": {
                    "cpu": "1",
                    "memory": "2Gi",
                    "nvidia.com/gpu": "1",
                },
                "limits": {
                    "cpu": "6",
                    "memory": "8Gi",
                    "nvidia.com/gpu": "1",
                },
            },
            "volumeMounts": [
                {
                    "name": "dshm",
                    "mountPath": "/dev/shm",
                },
                {
                    "name": "model-cache",
                    "mountPath": "/cache/huggingface",
                },
                {
                    "name": "tmp",
                    "mountPath": "/tmp",
                },
            ],
        }

    def _upsert_service(self, deployment: ModelDeployment) -> None:
        name = self._resource_name(deployment)

        body = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": name,
                "namespace": self._namespace,
                "labels": {
                    "app": name,
                    "managed-by": "private-llm-platform",
                },
            },
            "spec": {
                "selector": {
                    "app": name,
                },
                "ports": [
                    {
                        "port": 8000,
                        "targetPort": 8000,
                        "protocol": "TCP",
                    }
                ],
            },
        }

        try:
            self._core_api.patch_namespaced_service(
                name=name,
                namespace=self._namespace,
                body=body,
            )
        except Exception as exc:
            if not self._is_not_found_error(exc):
                raise KubernetesModelDeploymentError(
                    "Unable to update Kubernetes model service."
                ) from exc

            try:
                self._core_api.create_namespaced_service(
                    namespace=self._namespace,
                    body=body,
                )
            except Exception as create_exc:
                raise KubernetesModelDeploymentError(
                    "Unable to create Kubernetes model service."
                ) from create_exc

    def _require_catalog_entry(
        self,
        deployment: ModelDeployment,
    ) -> ModelCatalogEntry:
        if self._model_catalog is None:
            served_name = deployment.model.split("/")[-1].lower()

            return ModelCatalogEntry(
                model_id=self._slugify(served_name),
                display_name=served_name,
                engine=deployment.engine,
                engine_model_id=deployment.model,
                context_length=1024,
                served_model_name=served_name,
                gpu_required=True,
            )

        for entry in self._model_catalog.list_models():
            if entry.engine is not deployment.engine:
                continue

            identifiers = {
                entry.model_id,
                entry.engine_model_id,
                entry.benchmark_model_id,
            }

            if deployment.model in identifiers:
                return entry

        try:
            return self._model_catalog.get(deployment.model)
        except ModelNotFoundError as exc:
            raise KubernetesModelDeploymentError(
                f"Model '{deployment.model}' was not found in the catalog."
            ) from exc

    @staticmethod
    def _container_security_context() -> dict:
        return {
            "allowPrivilegeEscalation": False,
            "runAsNonRoot": True,
            "runAsUser": 10001,
            "runAsGroup": 10001,
            "readOnlyRootFilesystem": False,
            "capabilities": {
                "drop": ["ALL"],
            },
        }

    @staticmethod
    def _resource_name(deployment: ModelDeployment) -> str:
        if deployment.engine is LLMEngine.OLLAMA:
            return "ollama"

        clean_model = KubernetesModelDeploymentManager._slugify(
            deployment.model
        )
        return f"model-{deployment.engine.value}-{clean_model}"[:63].rstrip("-")

    @staticmethod
    def _slugify(value: str) -> str:
        return re.sub(
            r"[^a-z0-9]+",
            "-",
            value.lower(),
        ).strip("-")

    @staticmethod
    def _is_not_found_error(exc: Exception) -> bool:
        return getattr(exc, "status", None) == 404

    @staticmethod
    def _load_kubernetes_clients(
        *,
        context: str | None = None,
    ) -> tuple[object, object]:
        try:
            from kubernetes import client, config
        except ImportError as exc:
            raise KubernetesModelDeploymentError(
                "The kubernetes Python package is required for Kubernetes model management."
            ) from exc

        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config(context=context)

        return client.AppsV1Api(), client.CoreV1Api()