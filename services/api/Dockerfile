FROM python:3.11-slim
WORKDIR /app
COPY . /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app \
    PIP_DEFAULT_TIMEOUT=180  PIP_NO_CACHE_DIR=1

# 1) pip core
RUN python -m pip install --upgrade pip

# 2) lib cơ bản
RUN pip install --retries 10 --timeout 180 \
    fastapi uvicorn faiss-cpu scikit-learn numpy requests

# 3) TORCH CPU (từ index chính thức của PyTorch: rất nhanh & ổn định)
RUN pip install --retries 10 --timeout 300 \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.3.1 torchvision==0.18.1

# 4) ST + Transformers (từ PyPI)
RUN pip install --retries 10 --timeout 300 \
    sentence-transformers==2.7.0 transformers==4.43.3

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]

