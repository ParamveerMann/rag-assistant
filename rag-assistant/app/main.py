import logging, time
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from . import metrics as m
from . import rag
from .logging_conf import log, setup_logging

setup_logging()
logger = logging.getLogger("api")
app = FastAPI(title="Enterprise AI Knowledge Assistant")
MAX_MB = 20


@app.middleware("http")
async def observe(request: Request, call_next):
    t0 = time.time()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        path = route.path if route else "unmatched"
        dur = time.time() - t0
        if path != "/metrics":
            m.REQUESTS.labels(request.method, path, str(status)).inc()
            m.REQ_LATENCY.labels(path).observe(dur)
            log(logger, "request", method=request.method, path=path,
                status=status, duration_ms=round(dur * 1000))


class Ask(BaseModel):
    question: str


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        m.UPLOADS.labels("rejected").inc()
        raise HTTPException(400, "Only PDF files are supported")
    data = await file.read()
    if len(data) > MAX_MB * 1024 * 1024:
        m.UPLOADS.labels("rejected").inc()
        raise HTTPException(413, f"File exceeds {MAX_MB} MB")
    try:
        n = rag.index_pdf(file.filename, data)
    except ValueError as e:
        m.UPLOADS.labels("failed").inc()
        raise HTTPException(422, str(e))
    except Exception:
        m.UPLOADS.labels("failed").inc()
        logger.exception("upload_failure")
        raise HTTPException(500, "Failed to process PDF")
    m.UPLOADS.labels("ok").inc()
    return {"filename": file.filename, "chunks": n}


@app.post("/ask")
def ask(body: Ask):
    if not body.question.strip():
        raise HTTPException(400, "Question is empty")
    try:
        return rag.answer(body.question)
    except Exception:
        raise HTTPException(502, "LLM backend error")


@app.get("/")
def index():
    return FileResponse("app/static/index.html")


app.mount("/static", StaticFiles(directory="app/static"), name="static")
