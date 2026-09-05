# Kubernetes Metrics Server Requirement

## Purpose

The API HorizontalPodAutoscaler uses CPU utilization to decide when the API Deployment should scale.

The HPA configuration is stored in:

`kubernetes/local/api-hpa.yaml`

The HPA requires the Kubernetes resource metrics API.

## Required component

A Kubernetes cluster running this platform must provide Metrics Server or another compatible implementation of:

`metrics.k8s.io`

Without this API, the HPA cannot read CPU utilization and cannot make scaling decisions.

For the local Kind environment, this repository provides:

`kubernetes/local/metrics-server.yaml`

It includes `--kubelet-insecure-tls`, which is appropriate for the local Kind
certificate setup and should be reviewed before reuse on production clusters.

Install it with:

```bash
kubectl apply -f kubernetes/local/metrics-server.yaml
```

## Validation

After Metrics Server is installed, verify that the metrics API is available:

```bash
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl top pods -n llm-platform
kubectl get hpa -n llm-platform
```
