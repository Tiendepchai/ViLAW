FROM python:3.11-slim AS builder
WORKDIR /app
COPY . /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app \
    PIP_DEFAULT_TIMEOUT=180 PIP_NO_CACHE_DIR=1

RUN python -m pip install --upgrade pip \
    && pip install --retries 10 --timeout 180 \
        rq redis beautifulsoup4 lxml faiss-cpu scikit-learn numpy requests \
        pydantic-settings structlog \
    && pip install --retries 10 --timeout 300 \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.3.1 torchvision==0.18.1 \
    && pip install --retries 10 --timeout 300 \
        sentence-transformers==2.7.0 transformers==4.43.3

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app

RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import redis; r=redis.Redis('${REDIS_HOST:-redis}', ${REDIS_PORT:-6379}); r.ping()"

CMD ["python", "run_worker.py"]
