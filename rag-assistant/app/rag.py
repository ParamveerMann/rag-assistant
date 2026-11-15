import io, os, time, uuid, logging
from pypdf import PdfReader
from . import metrics as m
from .logging_conf import log

logger = logging.getLogger("rag")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma")
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
TOP_K = int(os.getenv("TOP_K", "4"))
_collection = None


def chunk_text(text: str, size: int = 800, overlap: int = 150):
    text = " ".join(text.split())
    if not text:
        return []
    step = max(size - overlap, 1)
    return [text[i:i + size] for i in range(0, len(text), step) if text[i:i + size].strip()]


def extract_pages(data: bytes):
    reader = PdfReader(io.BytesIO(data))
    return [(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)]


def get_collection():
    global _collection
    if _collection is None:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        # default embedding fn = local all-MiniLM-L6-v2 (no external API needed)
        _collection = client.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})
        m.CHUNKS.set(_collection.count())
    return _collection


def index_pdf(filename: str, data: bytes) -> int:
    col = get_collection()
    doc_id = uuid.uuid4().hex[:8]
    ids, docs, metas = [], [], []
    for page, text in extract_pages(data):
        for n, chunk in enumerate(chunk_text(text)):
            ids.append(f"{doc_id}-{page}-{n}")
            docs.append(chunk)
            metas.append({"source": filename, "page": page, "doc_id": doc_id})
    if not docs:
        raise ValueError("No extractable text (scanned PDF?)")
    col.add(ids=ids, documents=docs, metadatas=metas)
    m.CHUNKS.set(col.count())
    log(logger, "indexed", file=filename, chunks=len(docs), doc_id=doc_id)
    return len(docs)


def retrieve(question: str, k: int = TOP_K):
    col = get_collection()
    if col.count() == 0:
        return []
    with m.RETRIEVAL.time():
        res = col.query(query_texts=[question], n_results=min(k, col.count()))
    return [
        {"text": d, **meta}
        for d, meta in zip(res["documents"][0], res["metadatas"][0])
    ]


def answer(question: str):
    m.QUESTIONS.inc()
    ctx = retrieve(question)
    if not ctx:
        return {"answer": "No documents indexed yet. Upload a PDF first.", "sources": []}
    context = "\n\n".join(f"[{c['source']} p.{c['page']}]\n{c['text']}" for c in ctx)
    prompt = (
        "Answer the question using ONLY the context below. Cite sources as "
        "[file p.N]. If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    import anthropic
    t0 = time.time()
    try:
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        msg = client.messages.create(
            model=MODEL, max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
    except Exception:
        m.LLM_ERRORS.inc()
        logger.exception("llm_failure")
        raise
    finally:
        m.LLM_LATENCY.observe(time.time() - t0)
    log(logger, "answered", question_len=len(question), sources=len(ctx),
        llm_seconds=round(time.time() - t0, 2))
    return {"answer": text,
            "sources": [{"source": c["source"], "page": c["page"]} for c in ctx]}
