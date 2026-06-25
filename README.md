# Bộ Pháp Điển RAG — Hybrid Search (FAISS) + RQ + (tuỳ chọn) Ollama

Hệ thống tải dữ liệu **Bộ Pháp Điển** (phapdien.moj.gov.vn), làm sạch → chia đoạn → nhúng (embeddings) → lập chỉ mục FAISS, rồi cung cấp:
- **API tìm kiếm** (hybrid: keyword + embedding)
- **RAG trả lời có trích dẫn** (tuỳ chọn dùng LLM qua Ollama)

> Dự án phục vụ tra cứu/hỗ trợ tổng hợp. Không thay thế tư vấn pháp lý.

---

## Tính năng

- Pipeline end-to-end:
  - Download gói dữ liệu ZIP từ `BOPD_ZIP_URL`
  - Parse HTML, chuẩn hoá văn bản (`normalize_text`)
  - Xuất `JSONL` tài liệu sạch
  - Chunking theo dòng, có **overlap**
  - Embedding 2 chế độ:
    - `builtin`: HashingVectorizer (nhẹ, không cần model)
    - `st`: SentenceTransformers (chất lượng tốt hơn)
  - Lập chỉ mục **FAISS IndexFlatIP** (cosine ~ inner product sau normalize)

- Hybrid re-rank:
  - Tính điểm “khớp từ khoá” dựa trên `chu_de`, `de_muc`, `so_dieu`, `tieu_de_dieu`
  - Trộn với điểm tương đồng embedding theo trọng số động:
    - Query có “điều/khoản/mục/chương/tiểu mục” → ưu tiên exact match hơn

- Hàng đợi tác vụ (RQ + Redis):
  - Ingestor chỉ enqueue job refresh
  - Worker xử lý pipeline lâu (download/parse/embed/index)

- Updater:
  - Tự động gọi refresh theo lịch (mặc định ngày **1 & 16** hàng tháng lúc **03:30** theo `Asia/Ho_Chi_Minh`)
  - Chạy refresh 1 lần khi container start

---

## Kiến trúc

**Refresh pipeline** (xem `jobs/pipeline.py`):

1. `jobs/download.py`: tải ZIP → giải nén vào `DATA_DIR/raw/`
2. `jobs/parse_clean.py`: đọc HTML → xuất `DATA_DIR/bo_pd_clean.jsonl`
3. `jobs/chunk.py`: chunk `noi_dung` → `DATA_DIR/bo_pd_chunks.jsonl`
4. `jobs/embed_index.py`: embed + build FAISS → lưu `INDEX_DIR/bo_pd.index` & `INDEX_DIR/bo_pd_meta.json`

**Query**:

- `shared/search.py`: embed query → FAISS search → `shared/hybrid.py` rerank → trả hits
- `services/api/rag.py`: pack context + build prompt + gọi backend (`ollama` hoặc `summary`)

---

## Cấu trúc repo (tham chiếu)

> Repo thực tế có thể tách thư mục đúng như Docker Compose đang build (xem `docker-compose.yml`).

```
.
├─ docker-compose.yml
├─ .env.example
├─ shared/
│  ├─ config.py
│  ├─ text_norm.py
│  ├─ embedding.py
│  ├─ faiss_io.py
│  ├─ hybrid.py
│  └─ search.py
├─ jobs/
│  ├─ download.py
│  ├─ parse_clean.py
│  ├─ chunk.py
│  ├─ embed_index.py
│  └─ pipeline.py
└─ services/
   ├─ ingestor/   (FastAPI enqueue refresh)
   ├─ worker/     (RQ worker)
   ├─ api/        (search + rag endpoints)
   └─ updater/    (gọi refresh theo lịch)
```

---

## Yêu cầu

### Chạy bằng Docker (khuyến nghị)
- Docker + Docker Compose

### Chạy thuần Python (dev)
- Python 3.10+ (khuyến nghị)
- Thư viện chính:
  - `fastapi`, `uvicorn`
  - `redis`, `rq`
  - `faiss-cpu`, `numpy`
  - `beautifulsoup4`, `lxml`
  - `requests`
  - `scikit-learn` (cho `EMBEDDER_BACKEND=builtin`)
- Tuỳ chọn:
  - `sentence-transformers` (cho `EMBEDDER_BACKEND=st`)
  - `pytz` (để updater chạy theo timezone chính xác)

---

## Cấu hình (.env)

Các biến môi trường quan trọng (xem `shared/config.py` và `services/updater/app.py`):

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `BOPD_ZIP_URL` | URL file zip dữ liệu pháp điển | *(bắt buộc)* |
| `DATA_DIR` | thư mục dữ liệu | `/app/data` |
| `INDEX_DIR` | thư mục index | `/app/indexes` |
| `EMBEDDER_BACKEND` | `builtin` hoặc `st` | `builtin` |
| `EMBEDDER_MODEL` | model ST | `intfloat/multilingual-e5-small` *(trong config)* |
| `DEFAULT_ALPHA` | trọng số exact match | `0.6` |
| `DEFAULT_BETA` | trọng số embedding sim | `0.4` |
| `RAG_BACKEND` | `ollama` hoặc `summary` | `ollama` *(trong code rag.py)* |
| `RAG_MODEL` | model trên Ollama | `qwen2.5:7b` |
| `RAG_MAX_CHARS` | giới hạn context | `8000` |
| `TZ` | timezone cho updater | `Asia/Ho_Chi_Minh` |
| `MONTHLY_DAYS` | ngày chạy refresh | `1,16` |
| `DAILY_REFRESH_AT` | giờ chạy (HH:MM) | `03:30` |
| `REDIS_HOST`/`REDIS_PORT` | redis | `redis`/`6379` |
| `RQ_QUEUE` | tên queue | `bo_pd_jobs` |

---

## Quickstart (Docker Compose)

### 1) Tạo `.env`

Tạo file `.env` theo mẫu (tối thiểu cần `BOPD_ZIP_URL`).

### 2) Chạy

```bash
docker compose up -d --build
```

- Ingestor: `http://localhost:8081`
- API: `http://localhost:8080`

### 3) Refresh thủ công

```bash
curl -X POST http://localhost:8081/ingest/refresh
```

> Updater sẽ tự gọi refresh theo lịch cấu hình.

---

## API (gợi ý)

Vì phần `services/api` có thể thay đổi theo repo, dưới đây là pattern thường dùng:

- `GET /health` — healthcheck
- `GET /search?q=...&top_k=8` — trả hits (score + meta)
- `POST /rag` — body `{ "question": "...", "top_k": 6 }` → trả `{ answer, citations }`

---

## Vận hành & lưu ý

- **Dữ liệu lớn**: embedding + build index có thể tốn RAM/CPU.
- **Chất lượng parse**: `parse_clean.py` hiện dùng selector tương đối rộng (`.dieu, .dieu-item, .article, h3`) — tuỳ template HTML mà cần tinh chỉnh.
- **Tính chính xác**: RAG luôn yêu cầu “chỉ dùng trích dẫn”. Nếu thiếu căn cứ, hệ thống sẽ trả “Không đủ căn cứ trong trích dẫn”.
- **Bảo mật**: nếu expose public, cần thêm auth/rate-limit và lọc prompt injection.

---

## Đóng góp

Xem: `CONTRIBUTING.md`

---

## Giấy phép

GNU Affero General Public License v3.0 (AGPL-3.0). Xem: `LICENSE`

---

## Ghi công / Nguồn dữ liệu

- Nguồn dữ liệu: **Cổng thông tin điện tử pháp điển** (phapdien.moj.gov.vn) — được gắn trong `shared/config.py` dưới `SOURCE_NAME`.
