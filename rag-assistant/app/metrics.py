from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter("rag_http_requests_total", "HTTP requests", ["method", "path", "status"])
REQ_LATENCY = Histogram("rag_http_request_seconds", "HTTP latency", ["path"])
UPLOADS = Counter("rag_uploads_total", "PDF uploads", ["result"])
CHUNKS = Gauge("rag_chunks_indexed", "Chunks in vector store")
RETRIEVAL = Histogram("rag_retrieval_seconds", "Vector search latency")
LLM_LATENCY = Histogram("rag_llm_seconds", "LLM call latency",
                        buckets=(0.5, 1, 2, 4, 8, 16, 32))
LLM_ERRORS = Counter("rag_llm_errors_total", "LLM call failures")
QUESTIONS = Counter("rag_questions_total", "Questions asked")
