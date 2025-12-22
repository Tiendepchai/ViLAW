FROM python:3.11-slim
WORKDIR /app
COPY . /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app \
    PIP_DEFAULT_TIMEOUT=180  PIP_NO_CACHE_DIR=1

RUN python -m pip install --upgrade pip

RUN pip install --retries 10 --timeout 180 \
    rq redis beautifulsoup4 lxml faiss-cpu scikit-learn numpy requests

RUN pip install --retries 10 --timeout 300 \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.3.1 torchvision==0.18.1

RUN pip install --retries 10 --timeout 300 \
    sentence-transformers==2.7.0 transformers==4.43.3

CMD ["python", "run_worker.py"]

