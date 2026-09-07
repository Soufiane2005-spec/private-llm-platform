"""Tests for the Grafana Prometheus datasource manifest."""

from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parents[4]
DATASOURCE_FILE = (
    ROOT_DIR
    / "kubernetes"
    / "monitoring"
    / "grafana-prometheus-datasource.yaml"
)


def load_datasource_manifest() -> dict:
    """Load the Grafana datasource ConfigMap."""

    with DATASOURCE_FILE.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def test_grafana_datasource_configures_prometheus_service() -> None:
    """Grafana should discover Prometheus through Kubernetes service DNS."""

    manifest = load_datasource_manifest()

    assert manifest["kind"] == "ConfigMap"
    assert manifest["metadata"]["namespace"] == "monitoring"
    assert manifest["metadata"]["labels"]["grafana_datasource"] == "1"

    datasource = yaml.safe_load(manifest["data"]["prometheus-datasource.yaml"])
    prometheus = datasource["datasources"][0]

    assert prometheus["name"] == "Prometheus"
    assert prometheus["type"] == "prometheus"
    assert prometheus["url"] == (
        "http://monitoring-kube-prometheus-prometheus.monitoring:9090"
    )
    assert prometheus["isDefault"] is True
