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
```

## NGINX Ingress Controller

NGINX Ingress Controller routes external HTTP traffic to Kubernetes services.

Install Helm, then deploy the controller:

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --version 4.15.1
```

Validate the controller:

```bash
kubectl rollout status deployment/ingress-nginx-controller \
  -n ingress-nginx \
  --timeout=180s

kubectl get pods -n ingress-nginx
kubectl get ingressclass
```

## Local Test Ingress

Deploy the test application Ingress:

```bash
kubectl apply -f kubernetes/local/test-app-ingress.yaml
kubectl get ingress -n llm-platform
```

Test HTTP routing:

```bash
curl http://localhost/
```

On Docker Desktop for Windows, the internal LoadBalancer IP may not be directly reachable from the host. Use `localhost` for local validation.
## Persistent Model Storage

The platform uses a PersistentVolumeClaim to preserve downloaded LLM models across pod restarts.

Deploy the model storage:

```bash
kubectl apply -f kubernetes/local/model-storage-pvc.yaml
kubectl get pvc -n llm-platform