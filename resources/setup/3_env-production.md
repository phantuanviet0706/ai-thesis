# 3. `.env` production — sẵn để paste lên terminal VPS

`.env.example` (root repo) đã được dọn lại để khớp đúng `core/config.py::Setting` — không còn
biến `PG_*` (Postgres đã gỡ khỏi codebase, xem `2_docker-packaging.md` mục 2.6), có thêm ghi
chú biến nào thật sự được app đọc và biến nào chỉ phục vụ `docker-compose.yml`.

File này hướng dẫn tạo `.env` **thật** cho production — không commit file này vào git (đã có
trong `.gitignore`).

---

## 3.1. Sinh các secret bắt buộc phải đổi

Chạy trên VPS (hoặc máy local rồi copy giá trị), **không dùng giá trị mặc định trong
`.env.example`** cho bất kỳ mục nào dưới đây khi lên production:

```bash
# SECRET_KEY — ký JWT (core/security.py). Lộ key này = giả mạo được token bất kỳ user nào.
openssl rand -hex 32

# DB_PASSWORD — user ứng dụng dùng để kết nối MySQL (không phải root)
openssl rand -base64 24

# MYSQL_ROOT_PASSWORD — chỉ dùng lúc container mysql khởi tạo lần đầu, gần như không cần
# dùng lại sau đó (app kết nối bằng DB_USER/DB_PASSWORD, không phải root)
openssl rand -base64 24

# REDIS_PASSWORD — BẮT BUỘC không để trống khi lên production (xem cảnh báo mục 3.3)
openssl rand -base64 24

# TELEGRAM_WEBHOOK_SECRET — Telegram gửi lại trong header X-Telegram-Bot-Api-Secret-Token,
# adapter/telegram_adapter.py::verify_webhook so khớp giá trị này để chặn request giả mạo
openssl rand -hex 24
```

Chạy 5 lệnh trên, giữ lại output để điền vào file `.env` ở mục 3.2.

## 3.2. Nội dung `.env` production

Tạo file trực tiếp trên VPS bằng heredoc (dán cả khối vào terminal, thay các giá trị
`__REPLACE_ME__` bằng giá trị thật đã sinh ở mục 3.1 và API key thật của bạn):

```bash
cd /opt/pancharm/app

cat > .env <<'EOF'
# ── App ───────────────────────────────────────────────────────────────────
APP_NAME="Pancharm AI Retail Consultant"
APP_VERSION=1.0.0
APP_DESCRIPTION="Multi-Agent System for Feng Shui Jewelry Retail Consultation"
API_ENDPOINT=https://__YOUR_DOMAIN__
API_PATH=/api/v1

# ── MySQL — DB_HOST/REDIS_HOST bị docker-compose.yml override thành tên
#    service ("mysql"/"redis") khi chạy trong container, giữ nguyên ở đây
#    chỉ để không báo lỗi nếu chạy app ngoài Docker lúc debug.
DB_HOST=localhost
DB_PORT=3306
DB_USER=pancharm_app
DB_PASSWORD=__REPLACE_ME_DB_PASSWORD__
DB_NAME=pancharm_production
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# ── ChromaDB (embedded — path bên trong container, khớp volume mount) ───
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_PATH=./chroma_db

# ── LLM Provider ──────────────────────────────────────────────────────────
LLM_PROVIDER=anthropic

ANTHROPIC_API_KEY=__REPLACE_ME_ANTHROPIC_KEY__
ANTHROPIC_MODEL_PRIMARY=claude-sonnet-4-6
ANTHROPIC_MODEL_FAST=claude-haiku-4-5-20251001
ANTHROPIC_REASONING_EFFORT=medium
ANTHROPIC_REASONING_MIN_MAX_TOKENS=2048

GEMINI_API_KEY=__REPLACE_ME_GEMINI_KEY__
GEMINI_MODEL_PRIMARY=gemini-2.5-pro
GEMINI_MODEL_FAST=gemini-2.5-flash

OPENAI_API_KEY=

# ── Redis ─────────────────────────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=__REPLACE_ME_REDIS_PASSWORD__

# ── Auth (JWT) ────────────────────────────────────────────────────────────
SECRET_KEY=__REPLACE_ME_SECRET_KEY__
ALGORITHM=HS512
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_MINUTES=30

# ── CORS — domain frontend THẬT, không để localhost trên production ─────
ALLOWED_ORIGINS=["https://__YOUR_FRONTEND_DOMAIN__"]

# ── MinIO — chưa có service nào dùng, để mặc định ────────────────────────
MINIO_ENDPOINT=localhost:9002
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=123456789
MINIO_USE_SSL=false

# ── LangSmith tracing — bật nếu bạn có tài khoản, không bắt buộc ────────
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=pancharm-mas

# ── Telegram — điền sau khi domain + SSL đã sẵn sàng (mục 5), app tự gọi
#    setWebhook lúc startup (adapter/setup.py) ───────────────────────────
TELEGRAM_BOT_TOKEN=__REPLACE_ME_TELEGRAM_BOT_TOKEN__
TELEGRAM_WEBHOOK_SECRET=__REPLACE_ME_TELEGRAM_WEBHOOK_SECRET__
TELEGRAM_WEBHOOK_BASE_URL=https://__YOUR_DOMAIN__

# ── Messenger / Zalo — để trống, bạn tự setup sau (adapter/setup.py chỉ
#    đăng ký platform nào có token khai báo) ─────────────────────────────
MESSENGER_PAGE_ACCESS_TOKEN=
MESSENGER_APP_SECRET=
MESSENGER_VERIFY_TOKEN=
ZALO_OA_ACCESS_TOKEN=
ZALO_APP_SECRET=

# ── Kafka — để trống, app tự fallback sang BackgroundTasks ──────────────
KAFKA_BOOTSTRAP_SERVERS=
KAFKA_CLIENT_ID=pancharm-mas
KAFKA_CONSUMER_GROUP=pancharm-mas

# ── Chỉ docker-compose.yml đọc, Python app không đọc biến này ───────────
MYSQL_ROOT_PASSWORD=__REPLACE_ME_MYSQL_ROOT_PASSWORD__
EOF

chmod 600 .env   # chỉ owner đọc được — file này chứa API key thật
```

## 3.3. Cảnh báo bắt buộc đọc trước khi start

- **`REDIS_PASSWORD` không được để trống.** `docker-compose.yml` khởi tạo Redis Stack với
  `--requirepass ${REDIS_PASSWORD}` — nếu biến này rỗng, lệnh khởi động Redis nhận
  `--requirepass` không có giá trị theo sau và **container sẽ crash-loop**. Luôn set giá trị
  thật (mục 3.1).
- **`DB_USER` đổi từ `root` sang user riêng** (`pancharm_app` trong template trên) — tạo user
  này ở bước migrate (`4_data-seed-migrate.md`), tuân theo nguyên tắc least-privilege thay vì
  dùng root MySQL cho ứng dụng chạy production.
- **`ALLOWED_ORIGINS` phải là domain thật**, không để `http://localhost:5173` — nếu không,
  CORS sẽ chặn chính frontend production của bạn gọi API (hoặc tệ hơn, vẫn mở cho origin
  không mong muốn nếu bạn từng nới lỏng để test).
- **Không commit `.env`** — đã có trong `.gitignore` gốc của repo, xác nhận lại bằng
  `git check-ignore -v .env` trước khi làm bất kỳ `git add` nào trên VPS.
- **`LLM_PROVIDER`** — chọn 1 trong 2 (`anthropic` | `gemini`), chỉ cần API key của provider
  đang chọn là bắt buộc, key còn lại có thể để trống.

## 3.4. Xác nhận nhanh sau khi tạo `.env`

```bash
# Không có dòng nào chứa "REPLACE_ME" còn sót lại
grep -n "REPLACE_ME" .env && echo "❌ còn placeholder chưa điền" || echo "✔ OK"

# Quyền file đúng 600 (chỉ owner đọc/ghi)
stat -c "%a %n" .env
```

Xong bước này, sang `4_data-seed-migrate.md` để migrate schema + seed dữ liệu.
