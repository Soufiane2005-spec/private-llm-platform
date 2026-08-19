# vLLM Docker Deployment

Production-oriented Docker Compose deployment of vLLM with NVIDIA GPU support and an OpenAI-compatible API.

## Overview

This deployment provides:

- a pinned vLLM Docker image;
- NVIDIA GPU access;
- an OpenAI-compatible HTTP API;
- configurable model and runtime settings;
- a persistent Hugging Face model cache;
- CPU and memory limits;
- an automated health check;
- local-only API exposure by default.

## Architecture

The host exposes the vLLM API at:

```text
http://127.0.0.1:8000
```

Other containers on the vLLM Docker network use:

```text
http://vllm:8000
```

The default port mapping is:

```text
127.0.0.1:8000 -> container:8000
```

Binding the host port to `127.0.0.1` prevents direct access from other machines on the network.

## Files

```text
infrastructure/docker/vllm/
|-- compose.yaml
|-- compose.gpu-nvidia.yaml
`-- README.md
```

- `compose.yaml`: base vLLM configuration.
- `compose.gpu-nvidia.yaml`: NVIDIA GPU resource override.
- `README.md`: deployment and troubleshooting documentation.

## Requirements

- Docker Desktop with WSL2 integration;
- Docker Compose v2;
- an NVIDIA GPU and compatible driver;
- NVIDIA GPU support in Docker Desktop;
- enough GPU memory for the selected model.

Verify GPU availability:

```powershell
nvidia-smi
```

## Environment configuration

Create the local environment file when it does not exist:

```powershell
Copy-Item .env.example .env
```

Default vLLM variables:

```env
VLLM_IMAGE=vllm/vllm-openai:v0.27.0
VLLM_PORT=8000
VLLM_BASE_URL=http://vllm:8000
VLLM_MODEL=Qwen/Qwen3-0.6B
VLLM_SERVED_MODEL_NAME=qwen3-0.6b
VLLM_DTYPE=half
VLLM_GPU_MEMORY_UTILIZATION=0.80
VLLM_MAX_MODEL_LEN=1024
VLLM_MAX_NUM_SEQS=1
VLLM_LOGGING_LEVEL=INFO
VLLM_USE_V2_MODEL_RUNNER=0
HF_TOKEN=
```

Never commit the local `.env` file or a real Hugging Face token.

### WSL2 compatibility

`VLLM_USE_V2_MODEL_RUNNER=0` disables Model Runner V2. Some Docker Desktop and WSL2 environments do not expose the CUDA Unified Virtual Addressing capability required by Model Runner V2 and may fail with:

```text
RuntimeError: UVA is not available
```

The legacy model runner is therefore used as a compatibility mode for this local deployment.

## Validate the configuration

Run from the repository root:

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\vllm\compose.yaml `
  -f .\infrastructure\docker\vllm\compose.gpu-nvidia.yaml `
  config
```

## Pull the image

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\vllm\compose.yaml `
  -f .\infrastructure\docker\vllm\compose.gpu-nvidia.yaml `
  pull
```

## Start vLLM

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\vllm\compose.yaml `
  -f .\infrastructure\docker\vllm\compose.gpu-nvidia.yaml `
  up -d
```

The first startup may take several minutes while the image and model are downloaded.

## Check status

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\vllm\compose.yaml `
  -f .\infrastructure\docker\vllm\compose.gpu-nvidia.yaml `
  ps
```

Expected status:

```text
Up ... (healthy)
```

## View logs

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\vllm\compose.yaml `
  -f .\infrastructure\docker\vllm\compose.gpu-nvidia.yaml `
  logs -f vllm
```

A successful startup includes:

```text
Application startup complete
HTTP server started
GET /health HTTP/1.1 200 OK
```

Press `Ctrl+C` to stop following logs. This does not stop the container.

## List available models

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/v1/models" `
  -Method Get |
  ConvertTo-Json -Depth 5
```

The default served model name is `qwen3-0.6b`.

## Test text generation

```powershell
$body = @{
    model = "qwen3-0.6b"
    messages = @(
        @{
            role = "user"
            content = "Explain Docker in one simple sentence. /no_think"
        }
    )
    max_tokens = 128
    temperature = 0.2
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/v1/chat/completions" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

$response.choices[0].message.content
```

## Verify GPU usage

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\vllm\compose.yaml `
  -f .\infrastructure\docker\vllm\compose.gpu-nvidia.yaml `
  exec vllm nvidia-smi
```

A running server should display a Python process using GPU memory. `GPU-Util` may show `0%` while the model is idle.

## Persistent model cache

Downloaded models are stored in the Docker volume:

```text
private-llm-vllm-hf-cache
```

The cache survives normal container recreation. Do not add `-v` to `docker compose down` unless you intentionally want to delete the cached model.

## Stop the service

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\vllm\compose.yaml `
  -f .\infrastructure\docker\vllm\compose.gpu-nvidia.yaml `
  down
```

## Troubleshooting

### Port 8000 is already in use

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

Change `VLLM_PORT` in the local `.env` file if the port cannot be released.

### UVA is not available

Ensure the following value is present, then recreate the container:

```env
VLLM_USE_V2_MODEL_RUNNER=0
```

### CUDA out of memory

Use a smaller model or reduce the maximum context and concurrency:

```env
VLLM_MAX_MODEL_LEN=512
VLLM_MAX_NUM_SEQS=1
```

Do not increase GPU memory utilization without first checking available VRAM.

### Model download fails

Check internet connectivity, the model identifier, disk space, and `HF_TOKEN` for gated models.

## Security notes

- The host API is bound to `127.0.0.1` by default.
- Never commit `.env` or a real Hugging Face token.
- Authentication should be handled by the platform API instead of exposing vLLM directly.
