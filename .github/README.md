GitHub Actions workflows for the Private LLM Platform.

- `application-ci.yaml`: backend Ruff/Pytest and frontend ESLint/build.
- `api-image.yaml`: API container image build and GHCR push on `develop`.
- `docker-compose-ci.yaml`: Docker Compose validation for Ollama CPU/GPU files.
- `infrastructure-ci.yaml`: Kubernetes YAML, kubeconform, resource, security, HPA, PDB, rollout and secret-file checks.
