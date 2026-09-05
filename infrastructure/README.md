Infrastructure assets for the Private LLM Platform.

## Layout

- `docker/`: local Docker Compose configurations for Ollama and vLLM.
- `terraform/proxmox/`: reproducible Proxmox VM provisioning scaffold.
- `ansible/`: post-provisioning node preparation for Kubernetes hosts.

## Validation Scope

Docker Compose and Kubernetes manifests are validated by CI. Proxmox
provisioning requires real Proxmox API credentials, a VM template and network
access to a Proxmox VE host, so this repository provides reproducible IaC and
documents the environment limitation instead of claiming runtime provisioning.
