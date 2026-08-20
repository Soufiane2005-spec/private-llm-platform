# llm-d Kubernetes Preparation

## Status

Preparation only. The current local cluster is not approved for an llm-d
inference deployment because it does not expose an allocatable GPU.

Do not apply llm-d resources from this directory until all readiness checks are
satisfied.

## Scope

This directory documents the future Kubernetes integration of llm-d.

It intentionally contains no active llm-d deployment manifests. Production
manifests will be added only after the team selects compatible and pinned
versions for llm-d, Gateway API Inference Extension, and the model server.

## Current Cluster

| Property | Value |
|---|---|
| Cluster type | Local Kubernetes cluster |
| Control-plane node | `plateforme-llm-k8s-control-plane` |
| Kubernetes version | v1.36.1 |
| Helm version | v4.2.2 |
| Node status | Ready |
| Allocatable GPU | None |
| Inference/Gateway CRDs | Not installed |
| Deployment decision | Blocked |

## Why Deployment Is Blocked

The host has an NVIDIA RTX A500 Laptop GPU, but Kubernetes does not currently
advertise an `nvidia.com/gpu` resource.

A container running in the local Docker environment is not proof that a
Kubernetes workload can access the GPU. The Kubernetes node must expose the GPU
through a compatible device plugin before GPU workloads can be scheduled.

The current environment is suitable for:

- documentation validation;
- Kubernetes schema preparation;
- namespace and RBAC design;
- CI validation of future manifests;
- architecture planning.

It is not suitable for claiming a validated distributed inference deployment.

## Preflight Checks

Run these commands before any future installation:

```powershell
kubectl config current-context
kubectl cluster-info
kubectl get nodes -o wide
kubectl get nodes -o custom-columns="NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu"
kubectl get storageclass
kubectl get crd
helm version
Get-Command jq -ErrorAction SilentlyContinue
```

The preflight check passes only when:

- the expected cluster context is selected;
- all required nodes are `Ready`;
- at least one worker exposes an allocatable GPU;
- persistent storage is available;
- the required command-line tools are installed;
- the required Gateway and Inference CRDs are present or ready to be installed.

## Planned Components

A future deployment is expected to include:

1. a dedicated Kubernetes namespace;
2. Gateway API and Inference Extension resources;
3. the llm-d intelligent routing components;
4. one or more supported model-server workloads;
5. persistent model cache storage;
6. Kubernetes Secrets for protected registry credentials;
7. resource requests and limits;
8. health, readiness, and startup probes;
9. monitoring and benchmark integration;
10. restricted network access and RBAC.

## Version Pinning

Before implementation, record the selected versions in the deployment pull
request.

| Component | Required value |
|---|---|
| llm-d release | Pinned release required |
| Gateway API Inference Extension | Pinned release required |
| Model-server image | Pinned digest or version required |
| Model identifier | Explicit identifier required |
| Model revision | Pinned revision recommended |
| Kubernetes version | Compatibility must be verified |

Do not use floating `latest`, `main`, or unversioned remote manifests.

## Planned Deployment Sequence

When a compatible GPU cluster becomes available:

1. verify cluster access and GPU allocatable resources;
2. select and document compatible component versions;
3. install the required Gateway and Inference CRDs;
4. create a dedicated namespace;
5. configure secrets outside the repository;
6. configure persistent model storage;
7. deploy a minimal llm-d optimized baseline;
8. wait for all workloads to become ready;
9. test the health and model endpoints;
10. execute a reproducible inference smoke test;
11. collect latency, throughput, CPU, RAM, and GPU metrics;
12. compare results with direct vLLM deployment;
13. document rollback and cleanup results.

## Validation Requirements

A deployment pull request must provide evidence for:

- successful manifest rendering;
- successful Kubernetes server-side dry run;
- ready pods and healthy endpoints;
- a successful OpenAI-compatible inference request;
- visible GPU allocation and utilization;
- persistent model cache behavior;
- benchmark results;
- cleanup without orphaned resources.

## Security

- Never commit Hugging Face or registry tokens.
- Use Kubernetes Secrets or an approved external secret manager.
- Apply least-privilege RBAC.
- Keep inference services private by default.
- Expose traffic through the authenticated platform API.
- Define network policies before production exposure.
- Avoid including secret values in logs or benchmark reports.

## Rollback Plan

A future deployment must document:

- the namespace and release names;
- the command used to remove the selected release;
- CRDs that are shared with other workloads and must not be deleted blindly;
- persistent volumes that require explicit retention decisions;
- verification that no load balancers or GPU workloads remain active.

Persistent volumes and shared CRDs must never be deleted automatically without
confirming their ownership and retention policy.

## Repository Integration

llm-d will integrate with existing platform areas as follows:

- `services/api`: management and recommendation APIs;
- `domain/recommendations`: deployment strategy selection;
- `kubernetes`: versioned deployment resources;
- benchmark components: latency, throughput, and resource measurements;
- dashboard: deployment status and benchmark results.

## References

- [llm-d repository](https://github.com/llm-d/llm-d)
- [llm-d documentation](https://llm-d.ai/docs/)
- [llm-d guides](https://github.com/llm-d/llm-d/tree/main/guides)
- [Infrastructure prerequisites](https://github.com/llm-d/llm-d/blob/main/docs/infrastructure/README.md)
