# Private LLM Platform

A private platform for managing, serving, benchmarking and monitoring Large Language Models within a controlled infrastructure.

The project brings together LLM inference, backend services, asynchronous processing, Kubernetes orchestration, observability, security and CI/CD in one platform.

---

## Overview

Private LLM Platform provides a unified environment for operating LLM workloads through a web interface.

The platform supports:

- model management with Ollama and vLLM;
- private RAG over local documentation;
- asynchronous jobs for long-running operations;
- model benchmarking;
- Kubernetes-based deployment;
- monitoring with Prometheus and Grafana;
- authentication and role-based access control;
- automated validation with GitHub Actions.

The main objective is to manage the complete operational layer around LLM workloads rather than treating inference as an isolated service.

---

## Core Features

### Model Management

The platform provides a centralized catalog for LLM models and their assigned inference engines.

It distinguishes between:

- configured models;
- enabled models;
- inference engines;
- runtime availability;
- active deployments.

Supported inference engines:

- **Ollama**
- **vLLM**

---

### Private RAG Assistant

The platform includes a Retrieval-Augmented Generation assistant that searches local documentation before generating an answer.

The flow is:

```text
User Question
      |
      v
Local Retrieval
      |
      v
Relevant Context
      |
      v
LLM Inference
      |
      v
Grounded Response
