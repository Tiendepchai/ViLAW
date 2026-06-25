FROM python:3.11-slim
WORKDIR /app
COPY . /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app

RUN pip install --no-cache-dir fastapi uvicorn rq redis pydantic-settings structlog \
    && adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')"

EXPOSE 8081
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]
