# Technical Presentation Outline (10-12 slides)

1. **Problem & goal** - staff can't search PDFs; build a grounded Q&A assistant.
2. **Architecture diagram** - FastAPI, Chroma, Claude, K8s, Prometheus/Grafana/Loki (from README).
3. **RAG pipeline** - extract -> chunk(800/150) -> embed -> top-k=4 -> prompt "context only" -> cited answer.
4. **Key decisions** - local embeddings (no embeddings API at Anthropic); Chroma embedded; single replica and why.
5. **Containerization** - multi-stage-style slim image, non-root user, pre-baked embedding model, healthcheck.
6. **Kubernetes** - namespace, ConfigMap, Secret, PVC, Deployment with probes/limits, LoadBalancer Service.
7. **CI/CD** - GitHub Actions: lint/test -> build/push GHCR -> deploy (self-hosted runner).
8. **Observability: metrics** - custom metrics list; ServiceMonitor; dashboard panels.
9. **Observability: logs** - JSON logs -> Promtail -> Loki -> Grafana logs panel.
10. **Live demo** - upload PDF, ask, show citations, show dashboard moving, show logs line for the request.
11. **Verification** - `kubectl get pods`, `rollout status`, Prometheus target UP, tests green.
12. **Limitations & future work** - scaling vector DB, OCR, auth, evals, reranking.

## Demo script
1. `kubectl -n rag get pods` (Running 1/1)
2. Open http://localhost, upload sample PDF, ask 2 questions (one answerable, one not -> "I don't know")
3. Grafana: request rate, latency p95, LLM vs retrieval, chunk count, logs panel
4. Kill pod (`kubectl -n rag delete pod -l app=rag-assistant`) -> show self-healing and that data persists (PVC)
