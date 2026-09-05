# Proxmox Terraform

This directory provisions Kubernetes-ready virtual machines on Proxmox VE for
the Private LLM Platform.

It uses the actively maintained `bpg/proxmox` Terraform provider. The provider
version is constrained to the current `0.111.x` to `0.112.x` range so a future
provider release does not silently change VM behavior.

## Prerequisites

- Terraform or OpenTofu installed locally.
- Network access to a Proxmox VE API endpoint.
- A cloud-init capable Linux VM template already present on Proxmox.
- A Proxmox API token stored outside Git.
- SSH public key authorized through cloud-init.

## Usage

```powershell
cd infrastructure\terraform\proxmox
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan -out tfplan
terraform apply tfplan
```

Do not commit `terraform.tfvars`, `*.tfstate`, provider caches or API tokens.
The repository `.gitignore` already excludes Terraform state and local secret
material.

## Runtime Status

No Proxmox API endpoint or credentials are available in the current development
environment, so these files are IaC-ready but not runtime-provisioned here.
Validation is limited to static review unless a real Proxmox lab is connected.
