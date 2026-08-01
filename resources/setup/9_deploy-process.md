# 9. Quy trình deploy (các lần cập nhật sau)

`6_deployment-implementation.md` là runbook cho **lần đầu** (VPS trống → app chạy). File này
là quy trình cho **mỗi lần cập nhật code sau đó** — ngắn hơn nhiều vì hạ tầng đã sẵn.

---

## 9.1. Script deploy thủ công

File thật nằm ở `scripts/deploy.sh` trong repo (copy ra `/opt/pancharm/deploy.sh` một lần ở
Bước 1 — xem `6_deployment-implementation.md`). Nội dung:

```bash
# /opt/pancharm/deploy.sh
#!/bin/bash
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
#    upgrade, xem 4_data-seed-migrate.md mục 4.3)
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
```

Chạy: `/opt/pancharm/deploy.sh` — script tự gọi `/opt/pancharm/backup.sh` ở bước 1 (file
tương ứng: `scripts/backup.sh` trong repo, chi tiết `4_data-seed-migrate.md` mục 4.7).

## 9.2. Vì sao có `read -p` giữa chừng (không full tự động)

`main.py::lifespan` gọi `init_db()` (`create_all`) nhưng **không** tự chạy Alembic migration —
cố ý không tự động hoá bước này trong script vì `alembic revision --autogenerate` thỉnh
thoảng bắt sai diff (đổi tên cột bị hiểu nhầm thành drop+add, mất dữ liệu cột đó) — luôn cần
mắt người review file migration trước khi `upgrade head` chạy trên DB có dữ liệu thật. Nếu
sau này muốn CI/CD hoàn toàn tự động, tách bước migration thành review-and-merge riêng (vd
migration file được commit + review qua PR trước, script deploy chỉ chạy `upgrade head` với
migration đã có sẵn, không `--autogenerate` ngay trong lúc deploy).

## 9.3. Downtime thực tế

`docker compose up -d app` với 1 service: Docker dừng container cũ rồi start container mới —
có khoảng downtime bằng thời gian `get_compiled_graph()` pre-warm (vài giây tới ~30s tuỳ độ
trễ mạng tới Anthropic/Gemini lúc khởi tạo checkpointer/model). Với quy mô 1 VPS/1 instance,
đây là tradeoff chấp nhận được — zero-downtime thật sự cần ≥2 instance app chạy song song
sau load balancer, không hợp lý cho spec 6 vCPU/8GB hiện tại (xem giới hạn embedded ChromaDB
ở `2_docker-packaging.md` mục 2.5 — vốn đã giới hạn chỉ 1 instance).

Nếu cần giảm downtime hơn nữa mà chưa muốn scale ngang: cân nhắc thêm 1 `location` tạm thời
trả `503 Retry-After: 10` ở Nginx trong lúc container mới đang pre-warm, thay vì để client
nhận connection refused trong vài giây đó.

## 9.4. Rollback

```bash
cd /opt/pancharm/app

# Quay lại commit trước
git log --oneline -5           # xác định commit muốn rollback về
git checkout <COMMIT_HASH>

docker compose build app
docker compose up -d app
curl -s http://127.0.0.1:8088/health
```

Nếu lần deploy hỏng có kèm migration DB đã `upgrade head`: `alembic downgrade -1` **trước
khi** checkout code cũ (schema mới có thể incompatible với code cũ nếu downgrade sau). Luôn
kiểm tra `alembic/versions/` xem migration có viết đúng hàm `downgrade()` không (script.py.mako
mặc định sinh `downgrade()` đối xứng với `upgrade()`, nhưng autogenerate đôi khi bỏ sót
downgrade cho các thao tác phức tạp — review trước khi cần dùng thật, không phải lúc khẩn
cấp).

## 9.5. CI/CD qua GitHub Actions

File thật: `.github/workflows/deploy.yml`. Trigger tự động mỗi lần push lên `main` (đã chọn
auto-deploy thay vì chỉ bấm tay `workflow_dispatch`) — nghĩa là **mọi merge vào main sẽ tự
động lên production trong vài phút**, không có bước duyệt thủ công giữa chừng. Hệ quả trực
tiếp:

- Branch protection cho `main` (require PR review trước khi merge) gần như bắt buộc — nếu
  không, push thẳng lên main = deploy thẳng, bỏ qua toàn bộ review.
- Mọi migration DB phải được tạo (`alembic revision --autogenerate`), **review bằng mắt**,
  và commit vào `alembic/versions/` TRONG PR — không bao giờ tạo migration sau khi đã merge.
  `scripts/ci-deploy.sh` (bản không tương tác của `deploy.sh`) chạy thẳng
  `alembic upgrade head`, không có bước `read -p` chờ xác nhận như deploy thủ công.

2 job:

1. `smoke-test` — cài dependency + `python -c "import main"`, xác nhận toàn bộ import chain
   không lỗi cú pháp/thiếu module trước khi động vào VPS.
2. `deploy` — chỉ chạy nếu `smoke-test` pass, SSH vào VPS (qua `appleboy/ssh-action`) và chạy
   `/opt/pancharm/ci-deploy.sh` (đã copy sẵn từ `scripts/ci-deploy.sh`, xem Bước 1 ở
   `6_deployment-implementation.md`).

### Thiết lập secrets trên GitHub (làm 1 lần)

```bash
# Trên máy local (KHÔNG phải VPS) — tạo cặp key riêng cho CI, không dùng chung key SSH cá nhân
ssh-keygen -t ed25519 -f ~/.ssh/pancharm_ci -N "" -C "github-actions-deploy"

# Copy public key vào VPS, cho phép user 'deploy' login bằng key này
ssh-copy-id -i ~/.ssh/pancharm_ci.pub deploy@<VPS_IP>
```

Trên GitHub: **Settings → Secrets and variables → Actions → New repository secret**, thêm:

| Secret          | Giá trị                                              |
|-----------------|-------------------------------------------------------|
| `VPS_HOST`      | IP hoặc domain VPS                                     |
| `VPS_USER`      | `deploy`                                                |
| `VPS_SSH_KEY`   | Nội dung file **private** key (`~/.ssh/pancharm_ci`) — dán nguyên khối kể cả dòng `BEGIN/END` |
| `VPS_SSH_PORT`  | (tuỳ chọn) chỉ cần nếu đã đổi cổng SSH mặc định khỏi 22, xem `8_security-hardening.md` |

Không paste private key vào chat/AI — tự tạo và tự dán trực tiếp vào GitHub UI.

Nếu repo private và plan GitHub hỗ trợ (Pro/Team/Enterprise), có thể thêm **required
reviewer** cho environment `production` trong **Settings → Environments** để có 1 bước duyệt
tay trước khi job `deploy` chạy, dù trigger vẫn tự động — bù lại phần review đã mất khi bỏ
`workflow_dispatch`-only.

## 9.6. Checklist mỗi lần deploy

- [ ] Backup đã chạy (script tự làm ở bước 1, hoặc chạy tay trước nếu deploy ngoài giờ cron)
- [ ] Đã xem `git log HEAD..origin/main --oneline` — biết đang deploy gì
- [ ] Nếu có sửa `entity/*.py` — đã tạo + review migration trước khi upgrade
- [ ] `/health` trả `healthy` sau deploy
- [ ] Gửi thử 1 tin nhắn Telegram thật — xác nhận luồng end-to-end còn hoạt động (health check
      chỉ xác nhận MySQL/Chroma, không xác nhận được toàn bộ graph LangGraph chạy đúng)
- [ ] `docker compose logs app --tail=100` — không có traceback mới xuất hiện ngay sau start
