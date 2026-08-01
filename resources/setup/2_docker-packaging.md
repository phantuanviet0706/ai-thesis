# 2. Đóng gói ứng dụng (Docker)

Giải thích các file đã dựng ở root repo — `Dockerfile`, `docker-compose.yml`, `.dockerignore`
— và lý do đứng sau từng quyết định, để bạn hiểu rõ trước khi build trên VPS thật.

---

## 2.1. Vì sao multi-stage build

`Dockerfile` có 2 stage:

1. **`builder`** — cài `build-essential` + toàn bộ Python dependency, biên dịch mọi package
   cần compile (vd `cryptography`, `pydantic-core` bản chưa có wheel sẵn cho arch/Python
   version cụ thể).
2. **`runtime`** — chỉ copy `~/.local` (site-packages đã build) từ stage 1 sang, không có
   toolchain biên dịch. Image cuối nhẹ hơn đáng kể và giảm bề mặt tấn công (không có gcc,
   headers trong container chạy production).

## 2.2. torch CPU-only — khoản tiết kiệm lớn nhất

Mặc định `pip install torch` từ PyPI kéo theo wheel kèm CUDA runtime (~2.5-3GB, dành cho máy
có GPU NVIDIA). VPS này **không có GPU**, nên Dockerfile cài torch riêng từ index CPU-only
của PyTorch:

```dockerfile
RUN pip install --user --no-cache-dir torch==2.10.0 --index-url https://download.pytorch.org/whl/cpu
```

Kết quả: wheel torch giảm còn ~200MB, image build nhanh hơn, và RAM runtime của
`sentence-transformers` (dùng torch làm backend cho model embedding `all-MiniLM-L6-v2`) thấp
hơn hẳn vì không phải load các thư viện CUDA không dùng tới.

## 2.3. Dependency đã loại bỏ khỏi `requirements.txt`

Rà theo import thực tế trong codebase (không phải chỉ theo tên gói "nghe có vẻ liên quan"),
4 package sau **không được import ở bất kỳ đâu** trong source — xoá khỏi requirements để
giảm thời gian build + disk, không ảnh hưởng runtime:

| Package | Lý do loại |
|---|---|
| `underthesea`, `underthesea_core` | Thư viện NLP tiếng Việt — 0 chỗ import trong code, tokenize tiếng Việt thực tế đang dùng `unicodedata.normalize` thuần Python (`retrieval/hybrid_search.py::_tokenize_vi`) |
| `FlashRank` | Reranker — 0 chỗ import; hybrid search dùng `rank_bm25.BM25Okapi` (rank-bm25 vẫn giữ) |
| `psycopg2` | Driver Postgres — Postgres đã gỡ khỏi codebase (xem mục 2.6) |

`kubernetes==35.0.0` cũng được bỏ khỏi bản `requirements.txt` đã dọn — đây là dependency phụ
của `chromadb` chỉ cần cho chế độ Chroma server phân tán qua Kubernetes, không liên quan gì
tới cách project dùng ChromaDB (`PersistentClient` cục bộ, xem mục 2.5). Nếu sau này chuyển
sang Chroma server mode có auth qua K8s, cài lại package này.

`torch` vẫn còn trong `requirements.txt` (dùng làm dependency khai báo, không phải để pip tự
resolve) — Dockerfile luôn cài đè bản CPU-only trước khi cài phần còn lại, xem mục 2.2.

## 2.4. Model embedding được bake sẵn vào image

```dockerfile
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

Dòng này tải model `all-MiniLM-L6-v2` (~90MB) vào cache HuggingFace **ngay lúc build**, rồi
copy cache đó sang runtime stage. Lợi ích: container khởi động lại (restart, redeploy) không
cần gọi ra internet để tải lại model — nhanh hơn và không phụ thuộc mạng VPS lúc cold-start.

## 2.5. ChromaDB chạy embedded — không phải service riêng

`retrieval/chromadb_client.py` dùng `VectorDBManager` với `PersistentClient` trỏ vào
`CHROMA_PATH` (thư mục local) — không phải chế độ server (`HttpClient`). Vì vậy
`docker-compose.yml` **không có service `chromadb`** — dữ liệu vector nằm ngay trong volume
`./chroma_db` mount vào container `app`.

Hệ quả cần biết: vì chạy embedded, **chỉ được chạy đúng 1 instance app tại một thời điểm**
truy cập cùng thư mục `chroma_db` (đã có cơ chế retry trong `hybrid_search.py` cho trường hợp
2 process cùng ghi, nhưng đó là xử lý va chạm tạm thời với `scripts/seed_vectordb.py`, không
phải thiết kế cho nhiều instance app chạy song song lâu dài). Đây cũng là lý do Dockerfile
mặc định `--workers 1` (xem giải thích trong chính file Dockerfile).

## 2.6. Vì sao không có service Postgres/Kafka/MinIO

- **Postgres**: rà toàn bộ codebase thấy `database/postgres_manager.py` không được import ở
  bất kỳ file nào khác ngoài chính nó — nghĩa là `@DBManager.register_manager` không bao giờ
  chạy, Postgres **chưa từng thực sự được khởi tạo lúc runtime** dù có mặt trong
  `DBManager.init_all()`. Đã xoá hẳn file này + các biến `PG_*` khỏi `core/config.py` và
  `.env.example`. MySQL (qua `database/database.py`, engine riêng) mới là DB thật đang dùng
  cho toàn bộ ORM (`entity/`).
- **Kafka**: `main.py::lifespan` tự bọc try/except quanh `bot_producer.start()` — nếu
  `KAFKA_BOOTSTRAP_SERVERS` rỗng hoặc không kết nối được, app log warning và tiếp tục chạy,
  webhook rơi về xử lý trực tiếp qua `BackgroundTasks` (`api/v1/endpoints/webhook/webhook_controller.py`).
  Bỏ qua Kafka ở giai đoạn deploy này là an toàn, không cần sửa code.
- **MinIO**: biến `MINIO_*` chỉ tồn tại trong `core/config.py`, không có client MinIO nào
  được khởi tạo hay gọi ở bất kỳ service/repository nào trong code hiện tại — chưa cần deploy
  service này. Nếu sau này có tính năng upload ảnh dùng MinIO thật, thêm service vào
  `docker-compose.yml` lúc đó.

## 2.7. Build & chạy thử trên VPS

```bash
cd /opt/pancharm/app

# .env production đã chuẩn bị theo 3_env-production.md
docker compose build app

# Chưa start toàn bộ vội — xem 4_data-seed-migrate.md để migrate + seed DB trước,
# rồi mới `docker compose up -d` đầy đủ ở 6_deployment-implementation.md
```

## 2.8. Cấu hình vCPU/RAM có thể chỉnh sau

`docker-compose.yml` đặt `deploy.resources.limits` cố định cho từng service (app 3 vCPU/4GB,
mysql 1.5 vCPU/1.5GB, redis 1 vCPU/1GB — chừa ~0.5 vCPU/1.5GB cho host). Nếu về sau đo thực tế
thấy MySQL nhàn (ít truy vấn, app chưa nhiều traffic), có thể giảm giới hạn MySQL, tăng cho
`app` — sửa trực tiếp file này rồi `docker compose up -d` lại (không cần rebuild image).

Xem tiếp `3_env-production.md` để chuẩn bị `.env`.
