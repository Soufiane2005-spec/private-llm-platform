# Ansible Node Preparation

This playbook prepares Proxmox VMs for a Kubernetes installation by configuring
guest agent support, kernel modules, sysctl networking settings and swap.

It intentionally does not install a full Kubernetes distribution because the
target distribution can vary between labs. Use it before installing kubeadm,
k3s, RKE2 or another Kubernetes distribution.

## Usage

```powershell
cd infrastructure\ansible
Copy-Item inventory.example.ini inventory.ini
ansible-playbook -i inventory.ini site.yaml
```

GPU workers are marked with an explicit runtime requirement file. The actual
NVIDIA driver, container runtime and Device Plugin installation must be handled
for the real GPU hardware present in the Proxmox host.
