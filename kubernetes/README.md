# Kubernetes

Kubernetes manifests for the Private LLM Platform.

## Local Development Environment

The local development environment uses Kubernetes provided by Docker Desktop.

### Namespace

Project resources are deployed inside:

`llm-platform`

### Local Test Application

The initial infrastructure validation uses an NGINX application.

Files:

- `local/namespace.yaml`
- `local/test-app-deployment.yaml`
- `local/test-app-service.yaml`

### Deploy

```bash
kubectl apply -f kubernetes/local/namespace.yaml
kubectl apply -f kubernetes/local/test-app-deployment.yaml
kubectl apply -f kubernetes/local/test-app-service.yaml