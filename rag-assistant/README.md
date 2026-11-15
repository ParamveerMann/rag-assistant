# Enterprise AI Knowledge Assistant

Upload PDFs, ask questions, get answers grounded in your documents with page citations (RAG).

## Architecture
```
Browser ──> FastAPI (/upload, /ask, /metrics, /healthz)
              ├─ pypdf -> chunker (800 chars, 150 overlap)
              ├─ ChromaDB (persistent, local MiniLM embeddings)
              └─ Claude API (answers from top-k retrieved chunks only)
Prometheus ──scrapes /metrics──> Grafana
Promtail ──JSON stdout logs──> Loki ──> Grafana (Logs panel)
```
Embeddings are computed locally (Chroma default MiniLM) because the Anthropic API has no embeddings endpoint; only answer generation calls Claude.

## Run locally
```bash
export ANTHROPIC_API_KEY=sk-ant-...
docker compose up --build        # http://localhost:8000
```
Tests: `pip install -r requirements.txt ruff && pytest -q`

## Deploy to Docker Desktop Kubernetes
Enable Kubernetes in Docker Desktop settings, then:
```bash
docker build -t rag-assistant:local .
kubectl apply -f k8s/00-namespace.yaml
kubectl -n rag create secret generic anthropic --from-literal=ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
kubectl apply -f k8s/
kubectl -n rag rollout status deploy/rag-assistant
# App: http://localhost  (LoadBalancer on port 80)
```

## Monitoring and centralized logging
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring \
  --create-namespace -f monitoring/kube-prometheus-values.yaml
helm install loki grafana/loki-stack -n monitoring \
  --set grafana.enabled=false,promtail.enabled=true,loki.isDefault=false
kubectl apply -f monitoring/servicemonitor.yaml
kubectl -n monitoring create configmap rag-dashboard --from-file=monitoring/dashboard.json
kubectl -n monitoring label configmap rag-dashboard grafana_dashboard=1
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80   # admin / admin
```
Open Grafana -> Dashboards -> "RAG Knowledge Assistant". Prometheus targets: `kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090`.

## CI/CD (GitHub Actions)
`test` (ruff + pytest) -> `build-push` (image to GHCR, tagged by SHA) -> `deploy` (self-hosted runner on the Docker Desktop machine; enabled by repo variable `DEPLOY_LOCAL=true`).

## Metrics
`rag_http_requests_total`, `rag_http_request_seconds`, `rag_retrieval_seconds`, `rag_llm_seconds`, `rag_llm_errors_total`, `rag_uploads_total{result}`, `rag_chunks_indexed`, `rag_questions_total`.

## Design notes / limitations
- Single replica: Chroma is embedded with an RWO volume. To scale out, swap to a Chroma/Qdrant server and set `replicas > 1`.
- Scanned (image-only) PDFs are rejected; OCR would be a next step.
- No auth; add an Ingress with OIDC for real enterprise use.
