#!/bin/bash
# Chạy trên VPS tại /opt/pancharm/deploy.sh (copy ra khỏi repo, KHÔNG chạy từ trong app/).
# Quy trình đầy đủ: resources/setup/9_deploy-process.md
set -euo pipefail
cd /opt/pancharm/app

echo "[deploy] $(date) — bắt đầu"

# 1. Backup trước khi đổi bất cứ thứ gì — rollback được nếu deploy hỏng
/opt/pancharm/backup.sh

# 2. Lấy code mới
git fetch origin main
git log HEAD..origin/main --oneline    # xem trước sẽ deploy gì
git merge --ff-only origin/main

# 3. Build image mới (cache layer requirements.txt nếu không đổi — nhanh nếu chỉ sửa code)
docker compose build app

# 4. Migration schema NẾU có thay đổi entity/*.py trong lần cập nhật này — kiểm tra thủ công,
#    không tự động chạy autogenerate trong script (autogenerate cần review bằng mắt trước khi
#    upgrade, xem resources/setup/4_data-seed-migrate.md mục 4.3)
echo "[deploy] Nếu có sửa entity/*.py, chạy tay:"
echo "  docker compose run --rm app alembic revision --autogenerate -m \"...\""
echo "  docker compose run --rm app alembic upgrade head"
read -p "[deploy] Đã migrate xong (hoặc không cần) — Enter để tiếp tục restart app: "

# 5. Restart CHỈ service app — mysql/redis không bị động tới, tránh downtime dữ liệu
docker compose up -d app

# 6. Health check — chờ tối đa 60s cho app pre-warm graph xong (xem HEALTHCHECK trong Dockerfile)
for i in $(seq 1 12); do
    if curl -sf http://127.0.0.1:8088/health | grep -q '"status": "healthy"'; then
        echo "[deploy] ✔ healthy sau ${i}x5s"
        exit 0
    fi
    sleep 5
done

echo "[deploy] ❌ app KHÔNG healthy sau 60s — xem log:"
docker compose logs app --tail=50
exit 1
