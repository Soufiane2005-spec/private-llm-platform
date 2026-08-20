# Kubernetes Monitoring

The local Kubernetes environment uses `kube-prometheus-stack` for metrics, dashboards and alerting.

## Components

- Prometheus collects and stores metrics.
- Grafana displays metrics through dashboards.
- Alertmanager manages alerts.
- kube-state-metrics exposes Kubernetes metrics.
- node-exporter exposes node CPU, memory, disk and network metrics.

## Installation

```cmd
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace --version 88.5.0
```

## Validation

```cmd
kubectl get pods -n monitoring
helm list -n monitoring
```

## Grafana Access

```cmd
kubectl port-forward service/monitoring-grafana 3000:80 -n monitoring
```

Open `http://localhost:3000` and use the username `admin`.

Retrieve the generated password:

```cmd
kubectl get secret monitoring-grafana -n monitoring -o go-template="{{.data.admin-password | base64decode}}"
```

Never commit the generated password.

## Available Dashboards

- Kubernetes compute resources
- Kubernetes networking
- Persistent volumes
- Nodes
- Prometheus
- Kubernetes control-plane components