from fastapi.testclient import TestClient
from app.main import app
from app.rag import chunk_text

client = TestClient(app)


def test_chunk_overlap():
    chunks = chunk_text("a" * 2000, size=800, overlap=150)
    assert len(chunks) == 4 and all(len(c) <= 800 for c in chunks)


def test_chunk_empty():
    assert chunk_text("   ") == []


def test_health():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_metrics_exposed():
    client.get("/healthz")
    body = client.get("/metrics").text
    assert "rag_http_requests_total" in body


def test_rejects_non_pdf():
    r = client.post("/upload", files={"file": ("x.txt", b"hi", "text/plain")})
    assert r.status_code == 400
