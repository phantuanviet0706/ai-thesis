# 4. Migrate schema & seed dữ liệu

Thứ tự bắt buộc: **tạo DB + user MySQL → Alembic migrate schema → seed.sql (dữ liệu quan hệ)
→ seed_vectordb.py (đồng bộ sang ChromaDB)**. Đảo thứ tự sẽ lỗi (vd seed.sql chạy trước khi
có bảng, hoặc seed_vectordb.py chạy trước khi MySQL có dữ liệu để đọc).

Toàn bộ lệnh chạy từ `/opt/pancharm/app`, sau khi đã có `.env` production (mục 3).

---

## 4.1. Khởi động MySQL + Redis (chưa start app)

```bash
docker compose up -d mysql redis
docker compose ps    # đợi cả 2 ở trạng thái "healthy"
```

## 4.2. Tạo database + user ứng dụng (least-privilege)

Container `mysql` đã tự tạo database `${DB_NAME}` lúc khởi tạo lần đầu (biến
`MYSQL_DATABASE` trong `docker-compose.yml`) nhưng **chưa tạo user `pancharm_app`** — biến
`MYSQL_USER`/`MYSQL_PASSWORD` của image MySQL chính thức chỉ tạo user với quyền full trên
đúng 1 database đó, việc đó image đã tự làm. Xác nhận lại:

```bash
docker compose exec mysql mysql -u root -p"$(grep ^MYSQL_ROOT_PASSWORD .env | cut -d= -f2)" \
  -e "SELECT User, Host FROM mysql.user WHERE User='$(grep ^DB_USER .env | cut -d= -f2)';"
```

Nếu thấy 1 dòng kết quả → user đã tồn tại với đúng quyền, bỏ qua bước tạo thủ công. Nếu
trống (vd bạn đổi `DB_USER` sau khi container đã khởi tạo lần đầu), tạo tay:

```bash
docker compose exec mysql mysql -u root -p"$(grep ^MYSQL_ROOT_PASSWORD .env | cut -d= -f2)" <<'SQL'
CREATE DATABASE IF NOT EXISTS pancharm_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'pancharm_app'@'%' IDENTIFIED BY '__DB_PASSWORD_TU_.env__';
GRANT ALL PRIVILEGES ON pancharm_production.* TO 'pancharm_app'@'%';
FLUSH PRIVILEGES;
SQL
```

(thay `__DB_PASSWORD_TU_.env__` bằng đúng giá trị `DB_PASSWORD` trong `.env`)

## 4.3. Migrate schema bằng Alembic

`alembic/` đã được scaffold sẵn (`alembic.ini`, `alembic/env.py` đọc kết nối trực tiếp từ
`core.config.settings`, `alembic/env.py` import `entity` để nạp toàn bộ ORM model vào
`Base.metadata`). Đây là DB **trống** đầu tiên chạy Alembic nên cần tạo migration ban đầu
trước khi upgrade:

```bash
# Cài alembic vào cùng image app (đã có trong requirements.txt) rồi chạy qua container,
# để chắc chắn dùng đúng phiên bản Python/driver như lúc runtime
docker compose run --rm app alembic revision --autogenerate -m "initial schema"

# Đọc lại file vừa sinh ra trong alembic/versions/ — kiểm tra không có DROP TABLE nào
# ngoài ý muốn (autogenerate đôi khi bắt nhầm index/collation khác biệt không quan trọng)
cat alembic/versions/*_initial_schema.py

# Áp dụng migration
docker compose run --rm app alembic upgrade head
```

Từ lần deploy sau (khi sửa `entity/*.py` thêm cột/bảng mới), quy trình lặp lại đúng 2 lệnh
`alembic revision --autogenerate -m "..."` rồi `alembic upgrade head` — không cần đụng lại
bước 4.2.

> Ghi chú: `main.py::lifespan` vẫn gọi `init_db()` (`Base.metadata.create_all`) mỗi lần app
> khởi động — đây là lưới an toàn cho bảng hoàn toàn mới chưa kịp migrate, **không thay thế**
> Alembic vì `create_all` không alter bảng đã tồn tại. Luôn chạy `alembic upgrade head` sau
> khi đổi schema, đừng chỉ dựa vào `create_all`.

## 4.4. Seed dữ liệu quan hệ (MySQL)

`resources/migrate/seed.sql` (2660 dòng, đã có sẵn trong repo) chứa dữ liệu mẫu đầy đủ cho
demo/thesis defense — brands, categories, products, reviews, v.v., theo đúng thứ tự tôn
trọng foreign key:

```bash
docker compose exec -T mysql mysql -u root -p"$(grep ^MYSQL_ROOT_PASSWORD .env | cut -d= -f2)" \
  pancharm_production < resources/migrate/seed.sql
```

Xác nhận nhanh:

```bash
docker compose exec mysql mysql -u root -p"$(grep ^MYSQL_ROOT_PASSWORD .env | cut -d= -f2)" \
  -e "SELECT COUNT(*) AS products FROM pancharm_production.Products;"
```

Muốn seed lại từ đầu với data khác/nhiều hơn thay vì dùng file có sẵn:
`python scripts/generate_seed_data.py` (chạy local, sinh lại `resources/migrate/seed.sql`) —
không cần chạy trên VPS trừ khi bạn chủ động muốn thay bộ dữ liệu mẫu.

## 4.5. Đồng bộ ChromaDB (vector search cho KR Agent)

Chạy **sau khi** MySQL đã có dữ liệu (bước 4.4) — script đọc từ MySQL rồi ghi embedding vào
`chroma_db/`:

```bash
# Start app trước (cần import được toàn bộ module, nhưng script tự chạy độc lập không cần
# app đang serve request) — hoặc chạy trực tiếp qua docker compose run
docker compose run --rm app python scripts/seed_vectordb.py

# Kiểm tra thống kê 3 collection (product_overview / product_specs / product_reviews)
docker compose run --rm app python scripts/seed_vectordb.py --stats
```

Script chỉ index bản ghi `pending` theo mặc định (idempotent, chạy lại an toàn) — dùng
`--force` để re-index toàn bộ (cần khi đổi `EMBEDDING_MODEL_NAME` hoặc sửa hàng loạt dữ
liệu sản phẩm).

## 4.6. Xác nhận trước khi start toàn bộ stack

```bash
docker compose up -d
sleep 5
curl -s http://127.0.0.1:8088/health | python3 -m json.tool
```

Kỳ vọng: `{"status": "healthy", "checks": {"mysql": "ok", "chromadb": "ok"}}`. Nếu
`chromadb: fail` — kiểm tra volume `./chroma_db` có đúng quyền `appuser` (uid 1000, xem
Dockerfile) không bị root sở hữu do lần chạy trước bằng `docker compose run` với user khác.

## 4.7. Backup định kỳ (chạy bằng cron trên host, không phải trong container)

File thật nằm ở `scripts/backup.sh` trong repo, copy ra `/opt/pancharm/backup.sh` ở Bước 1
(`6_deployment-implementation.md`). Nội dung:

```bash
# /opt/pancharm/backup.sh
#!/bin/bash
set -e
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/pancharm/backups
mkdir -p "$BACKUP_DIR"

cd /opt/pancharm/app

# MySQL dump
docker compose exec -T mysql mysqldump -u root -p"$(grep ^MYSQL_ROOT_PASSWORD .env | cut -d= -f2)" \
  pancharm_production | gzip > "$BACKUP_DIR/mysql_${STAMP}.sql.gz"

# ChromaDB + LangGraph checkpoints (file-based, chỉ cần tar thư mục)
tar -czf "$BACKUP_DIR/chroma_${STAMP}.tar.gz" chroma_db/
tar -czf "$BACKUP_DIR/checkpoints_${STAMP}.tar.gz" data/

# Giữ lại 14 bản gần nhất, xoá cũ hơn
find "$BACKUP_DIR" -name "*.gz" -mtime +14 -delete
```

```bash
chmod +x /opt/pancharm/backup.sh
crontab -e
# Thêm dòng: chạy 3h sáng mỗi ngày
0 3 * * * /opt/pancharm/backup.sh >> /opt/pancharm/backup.log 2>&1
```

Khôi phục MySQL từ backup: `gunzip < mysql_STAMP.sql.gz | docker compose exec -T mysql mysql -u root -p"..." pancharm_production`.

## 4.8. Bảo trì định kỳ (không bắt buộc, chạy khi cần)

```bash
# Xoá thư mục segment ChromaDB mồ côi (phát sinh khi đổi embedding model/dims)
docker compose run --rm app python scripts/cleanup_chroma_orphans.py --dry-run
docker compose run --rm app python scripts/cleanup_chroma_orphans.py --yes

# Xoá dữ liệu hội thoại test/demo cũ trước khi seed lại cho môi trường sạch
docker compose run --rm app python scripts/reset_conversation_data.py
```

Xong bước này, sang `5_reverse-proxy-tls.md` để expose HTTPS ra internet.
