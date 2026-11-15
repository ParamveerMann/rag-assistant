FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd -m -u 10001 appuser && mkdir -p /data && chown appuser /data
USER appuser
# Pre-download the local embedding model so pods start offline-fast
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as D; D()(['warm'])"

COPY --chown=appuser app ./app
ENV CHROMA_PATH=/data/chroma
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request as u;u.urlopen('http://localhost:8000/healthz')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
