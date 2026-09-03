# Ollama and vLLM Non-Root Validation

## Current status

The API container runs as a dedicated non-root user.

Ollama and vLLM are not yet forced to run as non-root because their current writable paths are under `/root`.

## Ollama

Current writable model path:

`/root/.ollama`

This path is backed by the `model-storage` PersistentVolumeClaim.

Before enabling `runAsNonRoot`, the container image and persistent volume ownership must be validated for a dedicated UID/GID.

## vLLM

Current Hugging Face cache path:

`/root/.cache/huggingface`

This path is backed by the `vllm-model-cache` PersistentVolumeClaim.

Before enabling `runAsNonRoot`, the cache location and volume permissions must be migrated to a non-root writable path.

## Required future validation

For Ollama:

- select a dedicated UID/GID
- migrate model storage away from `/root`
- validate PVC ownership
- validate model pull and inference

For vLLM:

- select a dedicated UID/GID
- move `HF_HOME` away from `/root`
- validate PVC ownership
- validate model download and inference on an NVIDIA GPU node

Until those tests are completed, forcing `runAsNonRoot` could break model storage access.
