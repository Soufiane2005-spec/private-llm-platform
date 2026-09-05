locals {
  common_tags = [
    "private-llm-platform",
    "kubernetes",
  ]
}

resource "proxmox_virtual_environment_vm" "kubernetes_node" {
  for_each = var.cluster_nodes

  name      = each.key
  vm_id     = each.value.vm_id
  node_name = var.proxmox_node_name
  tags      = concat(local.common_tags, [each.value.role])

  clone {
    vm_id = var.template_vm_id
    full  = true
  }

  agent {
    enabled = true
  }

  cpu {
    cores = each.value.cpu_cores
    type  = "host"
  }

  memory {
    dedicated = each.value.memory_mb
  }

  disk {
    datastore_id = var.disk_datastore_id
    interface    = "scsi0"
    size         = each.value.disk_gb
  }

  initialization {
    datastore_id = var.cloud_init_datastore_id

    user_account {
      username = var.ssh_username
      keys     = var.ssh_public_keys
    }

    ip_config {
      ipv4 {
        address = each.value.ipv4_address
        gateway = var.gateway_ipv4
      }
    }
  }

  network_device {
    bridge = var.network_bridge
    model  = "virtio"
  }

  operating_system {
    type = "l26"
  }

  serial_device {}
}
