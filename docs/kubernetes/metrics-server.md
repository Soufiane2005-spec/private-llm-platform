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

## Validation

After Metrics Server is installed, verify that the metrics API is available:

```bash
kubectl get apiservice v1beta1.metrics.k8s.io
