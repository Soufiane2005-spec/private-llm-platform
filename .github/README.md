# Private LLM Platform

> A self-hosted platform for managing, serving, benchmarking and monitoring
> Large Language Models in a private infrastructure.

<p align="center">
  <strong>React · FastAPI · Ollama · vLLM · Kubernetes · Prometheus · Grafana</strong>
</p>

<p align="center">
  <img src="docs/assets/private-llm-platform-overview.png"
       alt="Private LLM Platform Overview"
       width="100%">
</p>

## Overview

Private LLM Platform provides a unified environment for operating LLM workloads
through a web interface.

The platform combines model management, local RAG, asynchronous processing,
performance benchmarking, Kubernetes orchestration, observability and CI/CD
within a single architecture.

## Core Capabilities

- **Model Management** — central catalog for Ollama and vLLM models
- **Private RAG** — query local documentation with grounded responses
- **Benchmarking** — latency, TTFT, throughput and resource measurements
- **Async Jobs** — tracked long-running operations with retry and DLQ support
- **Kubernetes** — deployment, storage, networking, scaling and availability
- **Observability** — Prometheus metrics and Grafana dashboards
- **Security** — authentication, RBAC, Secrets and NetworkPolicies
- **CI/CD** — automated testing, validation and API image builds
