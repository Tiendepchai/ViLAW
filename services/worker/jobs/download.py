import os, zipfile, io, urllib.request
from shared.config import ZIP_URL, DATA_DIR

RAW_DIR = os.path.join(DATA_DIR, "raw")

def run():
    os.makedirs(RAW_DIR, exist_ok=True)
    with urllib.request.urlopen(ZIP_URL) as r:
        buf = io.BytesIO(r.read())
    with zipfile.ZipFile(buf) as zf:
        zf.extractall(RAW_DIR)
    return {"raw_dir": RAW_DIR, "files": len(os.listdir(RAW_DIR))}

