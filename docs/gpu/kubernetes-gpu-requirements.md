# Kubernetes GPU Requirements

The vLLM Kubernetes deployment is configured to request:

- `nvidia.com/gpu: "1"`
- NVIDIA-compatible container runtime
- NVIDIA Device Plugin for Kubernetes
- NVIDIA GPU drivers on the Kubernetes node

## Local development limitation

The current development machine exposes only:

- Intel(R) UHD Graphics 620

No NVIDIA GPU is available to Windows, Docker Desktop, WSL, or Kubernetes.

Therefore:


- vLLM GPU runtime cannot be validated locally.
- The Kubernetes manifests are prepared for a GPU-capable cluster.
- Runtime validation must be performed on a node with an NVIDIA GPU.

## GPU cluster validation

On a GPU-capable cluster:

```bash
nvidia-smi
kubectl describe nodes | grep nvidia.com/gpu
kubectl get pods -A | grep nvidia
kubectl apply -f kubernetes/local/vllm-deployment.yaml
kubectl get pods -n llm-platform
```
