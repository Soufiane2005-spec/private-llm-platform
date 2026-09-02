"""Tests for Kubernetes Prometheus alerting rules."""

from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parents[4]

ALERTS_FILE = (
    ROOT_DIR
    / "kubernetes"
    / "monitoring"
    / "platform-alerts.yaml"
)


def load_alerts_manifest() -> dict:
    """Load the platform PrometheusRule manifest."""

    with ALERTS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return yaml.safe_load(file)


def get_alert_rules() -> list[dict]:
    """Return all alert rules from the manifest."""

    manifest = load_alerts_manifest()

    return manifest["spec"]["groups"][0]["rules"]


def get_rule_by_name(
    alert_name: str,
) -> dict:
    """Return a rule by alert name."""

    rules = get_alert_rules()

    for rule in rules:
        if rule["alert"] == alert_name:
            return rule

    raise AssertionError(
        f"Alert rule {alert_name!r} was not found."
    )


def test_alert_manifest_exists() -> None:
    """Prometheus alert manifest should exist."""

    assert ALERTS_FILE.is_file()


def test_alert_manifest_is_prometheus_rule() -> None:
    """Alert configuration should use the PrometheusRule CRD."""

    manifest = load_alerts_manifest()

    assert (
        manifest["apiVersion"]
        == "monitoring.coreos.com/v1"
    )

    assert manifest["kind"] == "PrometheusRule"

    assert (
        manifest["metadata"]["name"]
        == "llm-platform-alerts"
    )

    assert (
        manifest["metadata"]["namespace"]
        == "monitoring"
    )


def test_alert_manifest_has_monitoring_release_label() -> None:
    """Prometheus operator should discover the rule."""

    manifest = load_alerts_manifest()

    assert (
        manifest["metadata"]["labels"]["release"]
        == "monitoring"
    )


def test_alert_group_is_configured() -> None:
    """Platform alerts should belong to the expected rule group."""

    manifest = load_alerts_manifest()

    groups = manifest["spec"]["groups"]

    assert len(groups) == 1

    assert (
        groups[0]["name"]
        == "llm-platform.rules"
    )


def test_expected_alert_rules_are_present() -> None:
    """Manifest should contain all required platform alerts."""

    rules = get_alert_rules()

    alert_names = {
        rule["alert"]
        for rule in rules
    }

    assert alert_names == {
        "LLMPlatformDeploymentUnavailable",
        "LLMPlatformPodRestarting",
        "LLMPlatformPVCPending",
        "LLMPlatformStorageAlmostFull",
    }


def test_all_alerts_have_required_metadata() -> None:
    """Every alert should define operational metadata."""

    rules = get_alert_rules()

    for rule in rules:
        assert rule["expr"].strip()
        assert rule["for"]
        assert rule["labels"]["severity"]

        assert rule["annotations"]["summary"].strip()
        assert (
            rule["annotations"]["description"].strip()
        )


def test_alert_severities_are_supported() -> None:
    """Alerts should use known platform severity levels."""

    rules = get_alert_rules()

    valid_severities = {
        "warning",
        "critical",
    }

    for rule in rules:
        assert (
            rule["labels"]["severity"]
            in valid_severities
        )


def test_deployment_unavailable_alert() -> None:
    """Deployment alert should detect missing replicas."""

    rule = get_rule_by_name(
        "LLMPlatformDeploymentUnavailable"
    )

    expression = rule["expr"]

    assert (
        "kube_deployment_status_replicas_available"
        in expression
    )

    assert (
        "kube_deployment_spec_replicas"
        in expression
    )

    assert (
        'namespace="llm-platform"'
        in expression
    )

    assert rule["for"] == "5m"

    assert (
        rule["labels"]["severity"]
        == "critical"
    )


def test_pod_restarting_alert() -> None:
    """Pod restart alert should detect repeated crashes."""

    rule = get_rule_by_name(
        "LLMPlatformPodRestarting"
    )

    expression = rule["expr"]

    assert (
        "kube_pod_container_status_restarts_total"
        in expression
    )

    assert "increase(" in expression

    assert "[10m]" in expression

    assert "> 3" in expression

    assert (
        'namespace="llm-platform"'
        in expression
    )

    assert rule["for"] == "5m"

    assert (
        rule["labels"]["severity"]
        == "warning"
    )


def test_pvc_pending_alert() -> None:
    """PVC alert should detect pending storage claims."""

    rule = get_rule_by_name(
        "LLMPlatformPVCPending"
    )

    expression = rule["expr"]

    assert (
        "kube_persistentvolumeclaim_status_phase"
        in expression
    )

    assert (
        'namespace="llm-platform"'
        in expression
    )

    assert 'phase="Pending"' in expression

    assert "== 1" in expression

    assert rule["for"] == "10m"

    assert (
        rule["labels"]["severity"]
        == "warning"
    )


def test_storage_almost_full_alert() -> None:
    """Storage alert should detect capacity above 85 percent."""

    rule = get_rule_by_name(
        "LLMPlatformStorageAlmostFull"
    )

    expression = rule["expr"]

    assert (
        "kubelet_volume_stats_used_bytes"
        in expression
    )

    assert (
        "kubelet_volume_stats_capacity_bytes"
        in expression
    )

    assert (
        'namespace="llm-platform"'
        in expression
    )

    assert "* 100 > 85" in " ".join(
        expression.split()
    )

    assert rule["for"] == "10m"

    assert (
        rule["labels"]["severity"]
        == "critical"
    )