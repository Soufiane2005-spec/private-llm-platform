# Ollama Docker Deployment

Docker deployment of Ollama for the Private LLM Platform.

## Prerequisites

* Docker Desktop
* Docker Compose
* WSL2 on Windows
* NVIDIA GPU support in Docker for GPU execution

## Configuration

Create the local environment file from the repository root:

```powershell
Copy-Item .env.example .env
```

The default host port is `11434`. If it is already occupied, change only the local `.env` file:

```env
OLLAMA_PORT=11435
```

Inside the container, Ollama always listens on port `11434`.

## CPU deployment

Use this configuration on a machine without an NVIDIA GPU:

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\ollama\compose.yaml `
  up -d
```

## NVIDIA GPU deployment

Use the NVIDIA override to give Ollama access to the GPU:

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\ollama\compose.yaml `
  -f .\infrastructure\docker\ollama\compose.gpu-nvidia.yaml `
  up -d
```

## Check service health

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\ollama\compose.yaml `
  -f .\infrastructure\docker\ollama\compose.gpu-nvidia.yaml `
  ps
```

The service must report `healthy` before accepting inference requests.

## Pull the development model

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\ollama\compose.yaml `
  -f .\infrastructure\docker\ollama\compose.gpu-nvidia.yaml `
  exec ollama ollama pull llama3.2:1b
```

The model is stored in the persistent Docker volume.

## List installed models

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\ollama\compose.yaml `
  -f .\infrastructure\docker\ollama\compose.gpu-nvidia.yaml `
  exec ollama ollama list
```

## Test the API

From the Windows host, list the available models:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:11435/api/tags" `
  -Method Get
```

Change `11435` if another host port is configured in `.env`.

Run a generation request:

```powershell
$body = @{
    model = "llama3.2:1b"
    prompt = "Explain Docker in one simple sentence."
    stream = $false
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "http://127.0.0.1:11435/api/generate" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

$response.response
```

## Verify GPU usage

After running a generation request, execute:

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\ollama\compose.yaml `
  -f .\infrastructure\docker\ollama\compose.gpu-nvidia.yaml `
  exec ollama ollama ps
```

The `PROCESSOR` column should report GPU usage, for example:

```text
100% GPU
```

## Network access

From the host machine:

```text
http://127.0.0.1:${OLLAMA_PORT}
```

From another container connected to the Docker network:

```text
http://ollama:11434
```

The host port is bound to `127.0.0.1`, so the Ollama API is not exposed publicly.

## Persistent storage

Downloaded models are stored in the named volume:

```text
private-llm-ollama-models
```

Removing and recreating the container does not delete the models.

## View logs

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\ollama\compose.yaml `
  -f .\infrastructure\docker\ollama\compose.gpu-nvidia.yaml `
  logs --tail=50 ollama
```

## Stop the service

```powershell
docker compose --env-file .\.env `
  -f .\infrastructure\docker\ollama\compose.yaml `
  -f .\infrastructure\docker\ollama\compose.gpu-nvidia.yaml `
  down
```

Do not add `-v` unless you intentionally want to delete the persistent model volume and all downloaded models.
