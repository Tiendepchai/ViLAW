import os

DATA_DIR  = os.getenv("DATA_DIR", "/app/data")
INDEX_DIR = os.getenv("INDEX_DIR", "/app/indexes")
ZIP_URL   = os.getenv("BOPD_ZIP_URL")
EMBEDDER_BACKEND = os.getenv("EMBEDDER_BACKEND", "builtin")
EMBEDDER_MODEL   = os.getenv("EMBEDDER_MODEL", "intfloat/multilingual-e5-small")
DEFAULT_ALPHA = float(os.getenv("DEFAULT_ALPHA", "0.6"))
DEFAULT_BETA  = float(os.getenv("DEFAULT_BETA", "0.4"))
SOURCE_NAME = "Cổng thông tin điện tử pháp điển: phapdien.moj.gov.vn"

