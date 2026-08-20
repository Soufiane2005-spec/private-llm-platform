# LLM Engine Comparison

## Purpose

This document defines the qualitative comparison and deterministic selection
policy for the LLM engine deployments supported by the Private LLM Platform.

The comparison covers:

- Ollama;
- vLLM;
- supported deployment capabilities;
- operational constraints;
- deterministic selection rules.

Performance measurements such as latency, throughput, token rate, CPU, RAM, and
GPU usage are intentionally excluded. They belong to Tasks 29–35.

## Scope

The profiles in this document describe the deployments implemented in this
repository, not every configuration supported by the upstream projects.

Relevant deployment files:

```text
infrastructure/docker/ollama/
infrastructure/docker/vllm/
```

## Deployment comparison

| Criterion | Ollama deployment | vLLM deployment |
|---|---|---|
| Primary objective | Simple local model execution | Optimized model serving |
| Default model | `llama3.2:1b` | `Qwen/Qwen3-0.6B` |
| Host API | `127.0.0.1:11434` | `127.0.0.1:8000` |
| Docker API | `http://ollama:11434` | `http://vllm:8000` |
| Native API | Ollama REST API | OpenAI-compatible API |
| OpenAI compatibility | Partial compatibility available | Primary serving interface |
| Model management | Native pull, list, run, and remove commands | Hugging Face model loading |
| CPU fallback in repository | Supported | Not implemented |
| NVIDIA GPU deployment | Supported | Required by current Compose profile |
| Continuous batching profile | Not enabled in current configuration | Supported by the engine |
| High-throughput preference | No | Yes |
| Local-development preference | Yes | No |
| Persistent cache | Docker model volume | Hugging Face cache volume |
| Current concurrency limit | `OLLAMA_NUM_PARALLEL=1` | `VLLM_MAX_NUM_SEQS=1` |

## Validated local environment

The current development machine provides:

```text
GPU: NVIDIA RTX A500 Laptop GPU
VRAM: 4 GiB
```

Validated Ollama deployment:

- container reached healthy status;
- `llama3.2:1b` generated a response;
- model reported `100% GPU`;
- downloaded model persisted after container recreation.

Validated vLLM deployment:

- container reached healthy status;
- `/v1/models` exposed `qwen3-0.6b`;
- `/v1/chat/completions` generated a response;
- vLLM used approximately 3.35 GiB of GPU memory;
- Hugging Face model cache persisted after container recreation.

Because the GPU has only 4 GiB of VRAM, Ollama and vLLM must be evaluated
sequentially. Running both inference engines simultaneously is not supported by
the current local profile.

## Capability definitions

### `cpu_fallback`

The repository provides a deployment capable of running without an NVIDIA GPU.

### `local_development`

The deployment is optimized for simple local installation, model management,
and interactive use.

### `native_model_management`

The engine exposes built-in commands for downloading, listing, running, and
removing models.

### `openai_compatible_api`

The engine exposes at least part of the OpenAI API contract.

### `high_throughput_serving`

The engine is designed for optimized serving workloads.

### `continuous_batching`

The engine can dynamically batch incoming generation requests.

## Selection policy

The selector applies the following process:

1. remove deployments that do not satisfy available hardware;
2. remove deployments missing any required capability;
3. assign one point for every preferred capability matched;
4. select the deployment with the highest score;
5. choose Ollama when compatible deployments have equal scores;
6. return an explicit error when no deployment is compatible.

The default-order rule makes the result deterministic. It does not claim that
Ollama is universally faster or better than vLLM.

## Decision examples

| Situation | Result | Reason |
|---|---|---|
| No NVIDIA GPU | Ollama | Current vLLM profile requires NVIDIA |
| Simple local development | Ollama | Matches local-development preference |
| Native model management | Ollama | Provides native model commands |
| OpenAI API without GPU | Ollama | Compatible API and CPU fallback |
| High-throughput preference with GPU | vLLM | Matches optimized-serving preference |
| Continuous batching with GPU | vLLM | Matches continuous-batching capability |
| No preference and both compatible | Ollama | Deterministic default order |
| Required high throughput without GPU | Error | No compatible deployed profile |

## Error handling

The selector raises `NoCompatibleEngineError` when no deployment satisfies the
hard requirements.

Invalid configuration, such as duplicate engine profiles or a capability being
both required and preferred, raises `ValueError`.

The platform must expose these errors through the API layer later without
leaking internal stack traces.

## Current limitations

- The policy is qualitative and does not contain benchmark results.
- Scores represent matched capabilities, not measured performance.
- The current vLLM profile depends on an NVIDIA GPU.
- The current vLLM configuration limits concurrent sequences to one.
- The current Ollama configuration limits parallel requests to one.
- Model quality is not compared because the deployments use different models.
- Authentication is not part of Task 15.

## Future integration

Tasks 17–21 will expose engine information and selection through the platform
API.

Tasks 29–35 will provide measured latency, throughput, token rate, CPU, RAM,
and GPU results.

Tasks 41–45 will use benchmark results to improve the recommendation policy.

## References

- [Ollama API](https://docs.ollama.com/api/introduction)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [Ollama hardware support](https://docs.ollama.com/gpu)
- [vLLM documentation](https://docs.vllm.ai/en/latest/)
- [vLLM OpenAI-compatible server](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)