"""Tests for the API Kubernetes deployment manifest."""

from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parents[4]
API_DEPLOYMENT_FILE = (
    ROOT_DIR
    / "kubernetes"
    / "local"
    / "api-deployment.yaml"
)


def load_api_deployment() -> dict:
    """Load the local API Deployment manifest."""

    with API_DEPLOYMENT_FILE.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def test_api_deployment_configures_kubernetes_ollama_service() -> None:
    """API pods should call Ollama through the Kubernetes Service DNS name."""

    manifest = load_api_deployment()
    container = manifest["spec"]["template"]["spec"]["containers"][0]

    env = {
        item["name"]: item
        for item in container["env"]
    }

    assert env["OLLAMA_BASE_URL"]["value"] == "http://ollama:11434"


def test_api_deployment_can_read_auth_secret_from_kubernetes() -> None:
    """The API manifest should wire JWT signing material through a Secret."""

    manifest = load_api_deployment()
    container = manifest["spec"]["template"]["spec"]["containers"][0]

    env = {
        item["name"]: item
        for item in container["env"]
    }

    secret_key_ref = env["AUTH_SECRET_KEY"]["valueFrom"]["secretKeyRef"]

    assert secret_key_ref["name"] == "platform-secrets"
    assert secret_key_ref["key"] == "AUTH_SECRET_KEY"
    assert secret_key_ref["optional"] is True

    password_hash_ref = (
        env["AUTH_ADMIN_PASSWORD_HASH"]["valueFrom"]["secretKeyRef"]
    )

    assert password_hash_ref["name"] == "platform-secrets"
    assert password_hash_ref["key"] == "AUTH_ADMIN_PASSWORD_HASH"
    assert password_hash_ref["optional"] is True
