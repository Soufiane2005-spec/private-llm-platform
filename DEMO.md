# Private LLM Platform Demo

This script is designed for the final internship presentation. It shows the
functional platform first, then the operational evidence behind it.

## 1. Login

Start the API and frontend, then log in from the React top bar.

```powershell
$env:PYTHONPATH = "services/api/src"
services\api\.venv\Scripts\python.exe -m uvicorn interfaces.http.app:create_app --factory --host 127.0.0.1 --port 8000

cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Evidence:

- `GET /auth/me` returns the logged-in user.
- Admin users can open the Users view.
- Viewer users can read but cannot deploy, benchmark or manage users.

## 2. Models

Open the Models view.

Show:

- available model catalog entries
- engine names: Ollama and vLLM
- deployment status
- runtime state
- GPU availability when relevant
- error messages for failed deployments

## 3. Deploy

Deploy an Ollama model from the UI.

Equivalent API call:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/deployments `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"model":"llama3.2:1b","engine":"ollama"}'
```

Expected:

- API returns `202 Accepted` immediately.
- Response includes a `job_id`.
- Deployment starts as `deploying`.
- Jobs view updates through polling.
- Deployment becomes `running` only after the background operation completes.

For vLLM on a non-GPU cluster, show the controlled failure:

- deployment status: `failed`
- runtime state: `gpu-unavailable`
- job status: `failed`
- no fake `running` state

## 4. Jobs

Open the Jobs view.

Show:

- `pending`
- `running`
- `completed`
- `failed`
- attempts and retry budget
- queue size
- dead-letter count
- retained dead-letter failures

Equivalent API calls:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/jobs
Invoke-RestMethod http://127.0.0.1:8000/jobs/runtime
Invoke-RestMethod -Method Post http://127.0.0.1:8000/jobs/run-next
Invoke-RestMethod http://127.0.0.1:8000/jobs/dead-letter
```

## 5. Chat

Open the Chat view.

Ask:

```text
Comment retrouver une demande ?
```

Expected:

- answer is grounded in local Markdown demo documentation
- source file names are returned

Ask:

```text
astronomie galaxie satellite
```

Expected:

- strict fallback answer
- `sources=[]`
- no LLM call when no local source matches

## 6. Benchmark

Open the Benchmarks view.

Run a benchmark for one or more model/prompt pairs.

Show:

- total latency
- TTFT
- tokens generated
- tokens per second
- throughput
- CPU
- RAM
- GPU when available
- historical records
- comparison cards
- generated recommendation based on real recorded data

Equivalent API calls:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/benchmarks `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"model":"llama3.2:1b","engine":"ollama","prompts":["Donne un résumé court de la plateforme."]}'

Invoke-RestMethod http://127.0.0.1:8000/benchmarks
Invoke-RestMethod http://127.0.0.1:8000/benchmarks/report
```

Do not present fabricated benchmark history. Empty state is acceptable before
real runs.

## 7. Monitoring

Open the Monitoring view.

Show:

- CPU
- RAM
- GPU field when available
- model runtime states
- pod readiness
- alerts
- Prometheus-backed dashboard values when `PROMETHEUS_BASE_URL` is configured

Equivalent API call:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/dashboard
```

## 8. Grafana

Expose Grafana from the monitoring namespace when the cluster is available.

```powershell
kubectl get svc -n monitoring
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
```

Open:

```text
http://127.0.0.1:3000
```

If the local Kubernetes cluster is unavailable, state that Grafana access is an
environment limitation for the current run.

## 9. Kubernetes

Run the cluster checks when Docker Desktop and Kind are available.

```powershell
kubectl cluster-info
kubectl get nodes
kubectl get pods -A
kubectl get pods -n llm-platform
kubectl get svc -n llm-platform
kubectl get pvc -n llm-platform
kubectl get hpa -n llm-platform
kubectl get pdb -n llm-platform
kubectl get networkpolicy -n llm-platform
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl top pods -n llm-platform
```

Validate manifests:

```powershell
kubectl apply --dry-run=server -f kubernetes/local
kubectl apply --dry-run=server -f kubernetes/monitoring
```

Runtime claims require a live cluster. If Docker Desktop is stopped, report the
cluster validation as unavailable, not passed.

## 10. CI/CD

Show the workflows:

- `.github/workflows/application-ci.yaml`
- `.github/workflows/api-image.yaml`
- `.github/workflows/docker-compose-ci.yaml`
- `.github/workflows/infrastructure-ci.yaml`

Explain:

- pull requests run backend tests, coverage, Ruff, frontend lint/build and
  manifest checks
- `develop` builds and pushes the API image to GHCR with a SHA tag
- no production `latest` tag is used
- no deployment secret is committed

## Final Local Validation

```powershell
git status --short --branch
git fetch origin
git log --oneline HEAD..origin/develop
git diff --check

services\api\.venv\Scripts\python.exe -m ruff check services\api\src services\api\tests
services\api\.venv\Scripts\python.exe -m pytest services\api\tests

cd frontend
npm run lint
npm run build
cd ..
```

Docker, Kubernetes, Terraform and Ansible runtime validation must be reported
separately because they depend on local services and external credentials.
