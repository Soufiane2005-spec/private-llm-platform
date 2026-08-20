# llm-d Integration Preparation

## Status

Planning only. Task 16 does not deploy llm-d to the local development cluster.

## Purpose

llm-d is a Kubernetes-native distributed inference stack. It orchestrates model
servers such as vLLM and adds production capabilities including intelligent
routing, distributed inference, KV-cache management, and operational controls.

llm-d is not treated as a third LLM engine in this platform:

- Ollama is the local and developer-oriented inference engine.
- vLLM is the high-throughput OpenAI-compatible inference engine.
- llm-d is a future Kubernetes orchestration layer above model servers such as
  vLLM.

Therefore, llm-d must not be added to the `LLMEngine` domain enumeration.

## Local Environment Assessment

Assessment date: 2026-08-20.

| Requirement | Local environment | Status |
|---|---|---|
| Kubernetes cluster | Available | Ready |
| Kubernetes version | v1.36.1 | Compatible |
| Helm | v4.2.2 | Available |
| Kubernetes node | `plateforme-llm-k8s-control-plane` | Ready |
| GPU visible to Windows | NVIDIA RTX A500 Laptop GPU, 4 GB | Available |
| GPU allocatable by Kubernetes | None | Blocked |
| Gateway API Inference Extension CRDs | Not installed | Missing |
| Distributed accelerator capacity | Not available | Blocked |

The local cluster can validate Kubernetes resources and documentation, but it
cannot run a realistic llm-d inference deployment because no GPU resource is
exposed to Kubernetes.

## Architecture Decision

Task 16 prepares the repository for a future llm-d deployment without adding
unverified production manifests.

The target architecture is:

1. The platform API receives an inference or benchmark request.
2. The recommendation layer chooses the appropriate serving strategy.
3. Ollama remains available for lightweight local inference.
4. vLLM remains available for direct single-engine GPU inference.
5. llm-d may orchestrate multiple model-server replicas on a GPU-enabled
   Kubernetes cluster.
6. The benchmark system supplies performance data to future recommendations.

## Future llm-d Responsibilities

A future llm-d integration may provide:

- load-aware and prefix-cache-aware routing;
- orchestration of multiple vLLM replicas;
- distributed prefill and decode workloads;
- KV-cache-aware scheduling and offloading;
- autoscaling and flow control;
- integration with Kubernetes Gateway API;
- production observability and benchmark-driven optimization.

These capabilities remain outside the current local MVP.

## Deployment Prerequisites

Before enabling llm-d, the target environment must provide:

- a supported Kubernetes cluster;
- one or more accelerator-enabled worker nodes;
- a working GPU device plugin;
- sufficient GPU memory for the selected models;
- persistent model storage;
- `kubectl`, Helm, and required command-line dependencies;
- Gateway API and Inference Extension CRDs;
- cluster permissions for the required resources;
- network access to the selected model registry;
- Kubernetes Secrets for protected model registry credentials;
- monitoring for latency, throughput, errors, and resource usage.

## Security Requirements

- Never commit Hugging Face tokens or registry credentials.
- Store credentials in Kubernetes Secrets or an external secret manager.
- Use namespace-scoped service accounts and least-privilege RBAC.
- Do not expose model-server endpoints publicly by default.
- Route external requests through the platform API and authentication layer.
- Pin deployment and container versions before production use.

## Versioning Policy

The implementation must not use unpinned `latest` or `main` versions.

Before deployment, the team must explicitly select and document:

- the llm-d release;
- the Gateway API Inference Extension version;
- the model-server image version;
- the model identifier and revision;
- the Kubernetes compatibility range.

Versions will be selected during the real deployment task after validation
against the target GPU cluster.

## Readiness Criteria

A real llm-d deployment may begin only when:

- [ ] Kubernetes GPU resources are visible through `nvidia.com/gpu`;
- [ ] the target model fits the available accelerator capacity;
- [ ] Gateway API and Inference Extension versions are pinned;
- [ ] persistent storage is available;
- [ ] required secrets are configured outside Git;
- [ ] resource requests and limits are defined;
- [ ] health checks and monitoring are configured;
- [ ] rollback and cleanup procedures are documented;
- [ ] a reproducible smoke test is available.

## Current Decision

The repository will contain preparation documentation only.

No llm-d workload will be deployed on the current local cluster. This avoids
claiming support that cannot be validated with the available hardware.

## Future Work

- provision or access a GPU-enabled Kubernetes cluster;
- install and validate the required Gateway API extensions;
- select a pinned llm-d release;
- prepare a minimal optimized-baseline deployment;
- connect llm-d to the platform management API;
- benchmark direct vLLM against llm-d-managed vLLM;
- use benchmark results in the recommendation layer.

## References

- [llm-d repository](https://github.com/llm-d/llm-d)
- [llm-d documentation](https://llm-d.ai/docs/)
- [llm-d guides](https://github.com/llm-d/llm-d/tree/main/guides)
- [llm-d infrastructure prerequisites](https://github.com/llm-d/llm-d/blob/main/docs/infrastructure/README.md)
