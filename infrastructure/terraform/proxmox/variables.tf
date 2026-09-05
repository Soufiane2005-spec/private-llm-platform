variable "proxmox_endpoint" {
  description = "Proxmox API endpoint, for example https://pve.example.local:8006/."
  type        = string
}

variable "proxmox_api_token" {
  description = "Proxmox API token in the format user@realm!token=secret."
  type        = string
  sensitive   = true
}

variable "proxmox_tls_insecure" {
  description = "Allow self-signed Proxmox certificates in local labs."
  type        = bool
  default     = false
}

variable "proxmox_node_name" {
  description = "Proxmox node where the VMs are created."
  type        = string
}

variable "template_vm_id" {
  description = "Existing cloud-init capable template VM ID to clone."
  type        = number
}

variable "disk_datastore_id" {
  description = "Proxmox datastore for VM disks."
  type        = string
  default     = "local-lvm"
}

variable "cloud_init_datastore_id" {
  description = "Proxmox datastore for cloud-init disks."
  type        = string
  default     = "local-lvm"
}

variable "network_bridge" {
  description = "Linux bridge connected to the Kubernetes network."
  type        = string
  default     = "vmbr0"
}

variable "ssh_username" {
  description = "Initial cloud-init SSH user."
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_keys" {
  description = "SSH public keys authorized for the initial user."
  type        = list(string)
}

variable "gateway_ipv4" {
  description = "IPv4 gateway used when VM addresses are static."
  type        = string
  default     = null
}

variable "cluster_nodes" {
  description = "Kubernetes VMs to create on Proxmox."
  type = map(object({
    vm_id        = number
    role         = string
    cpu_cores    = number
    memory_mb    = number
    disk_gb      = number
    ipv4_address = string
  }))

  validation {
    condition = alltrue([
      for node in var.cluster_nodes :
      contains(["control-plane", "worker", "gpu-worker"], node.role)
    ])
    error_message = "Node role must be control-plane, worker, or gpu-worker."
  }
}
