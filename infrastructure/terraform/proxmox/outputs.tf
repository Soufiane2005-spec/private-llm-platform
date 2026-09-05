output "kubernetes_nodes" {
  description = "Provisioned Kubernetes VM metadata for Ansible inventory."
  value = {
    for name, vm in proxmox_virtual_environment_vm.kubernetes_node : name => {
      vm_id = vm.vm_id
      role  = var.cluster_nodes[name].role
      ipv4  = var.cluster_nodes[name].ipv4_address
    }
  }
}
