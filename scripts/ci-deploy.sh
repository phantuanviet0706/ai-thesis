#!/bin/bash
# Bản KHÔNG tương tác của scripts/deploy.sh — dùng cho GitHub Actions (.github/workflows/deploy.yml).
# Chạy trên VPS tại /opt/pancharm/ci-deploy.sh (copy ra khỏi repo cùng lúc với deploy.sh/backup.sh).
#
# Khác deploy.sh ở đúng 1 chỗ: không có `read -p` chờ người xác nhận migration — thay vào
# đó chạy thẳng `alembic upgrade head` (không --autogenerate). Điều này AN TOÀN chỉ khi migration
# file đã được tạo bằng `alembic revision --autogenerate`, REVIEW BẰNG MẮT, và commit vào
# alembic/versions/ trước khi merge vào main — không bao giờ autogenerate ngay trong lúc deploy
# (xem resources/setup/4_data-seed-migrate.md mục 4.3 và 9_deploy-process.md mục 9.2/9.5).
set -euo pipefail
cd /opt/pancharm/app

echo "[ci-deploy] $(date) — bắt đầu"

# 1. Backup trước khi đổi bất cứ thứ gì — rollback được nếu deploy hỏng
/opt/pancharm/backup.sh

# 2. Lấy code mới (workflow đã checkout đúng commit trên main, ở đây chỉ đồng bộ VPS)
git fetch origin main
git merge --ff-only origin/main

# 3. Build image mới
docker compose build app

# 4. Migration — idempotent, không autogenerate. Nếu không có migration mới thì no-op.
docker compose run --rm app alembic upgrade head

# 5. Restart CHỈ service app — mysql/redis không bị động tới
docker compose up -d app

# 6. Health check — chờ tối đa 60s cho app pre-warm graph xong
for i in $(seq 1 12); do
    if curl -sf http://127.0.0.1:8088/health | grep -q '"status": "healthy"'; then
        echo "[ci-deploy] ✔ healthy sau ${i}x5s"
        exit 0
    fi
    sleep 5
done

echo "[ci-deploy] ❌ app KHÔNG healthy sau 60s — xem log:"
docker compose logs app --tail=50
exit 1
