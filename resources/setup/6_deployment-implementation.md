# 6. Triển khai chi tiết — runbook end-to-end

Gộp toàn bộ các bước từ file 1-5 thành 1 trình tự chạy thẳng cho lần deploy đầu tiên, từ VPS
trống tới app chạy production với HTTPS + Telegram webhook hoạt động. Dùng file này như
checklist chính; quay lại file tương ứng (1-5) nếu cần giải thích **vì sao** một bước tồn tại.

Áp dụng cho: Ubuntu 22.04/24.04, 6 vCPU / 8GB RAM / 60GB SSD, domain đã trỏ A record về VPS.

---

## Bước 0 — Trên máy local, trước khi lên VPS

- [ ] Đã có repo với `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `alembic/`,
      `.env.example` đã dọn (không còn `PG_*`), `requirements.txt` đã trim.
- [ ] Đã `git push` toàn bộ lên remote (VPS sẽ `git clone`/`git pull`, không copy tay).
- [ ] Đã có: Anthropic hoặc Gemini API key, Telegram bot token (từ @BotFather).
- [ ] Domain đã trỏ A record về IP VPS (`dig +short __YOUR_DOMAIN__` phải ra đúng IP).

## Bước 1 — Hạ tầng VPS (chi tiết: `1_vps-infrastructure.md`)

```bash
ssh root@<VPS_IP>
adduser deploy && usermod -aG sudo deploy
# (từ máy local) ssh-copy-id deploy@<VPS_IP>
ssh deploy@<VPS_IP>

sudo apt update && sudo apt upgrade -y
sudo timedatectl set-timezone Asia/Ho_Chi_Minh

# Swap 4GB
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Docker Engine + Compose V2
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh && rm get-docker.sh
sudo usermod -aG docker deploy && newgrp docker

# Firewall
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw enable

# Nginx + Certbot
sudo apt install -y nginx certbot python3-certbot-nginx

# Clone source
sudo mkdir -p /opt/pancharm && sudo chown deploy:deploy /opt/pancharm
cd /opt/pancharm && git clone __URL_REPO__ app && cd app

# deploy.sh/backup.sh sống trong repo ở scripts/ — copy ra /opt/pancharm/ (KHÔNG chạy từ
# trong app/, vì deploy.sh sẽ tự git merge đè lên chính nó nếu chạy tại chỗ)
cp scripts/deploy.sh scripts/backup.sh /opt/pancharm/
chmod +x /opt/pancharm/deploy.sh /opt/pancharm/backup.sh
```

Checklist đầy đủ + phần hardening SSH: xem `1_vps-infrastructure.md` mục 1.9 và
`8_security-hardening.md` — làm hardening SSH **ngay sau** bước này, trước khi mở app ra
internet.

## Bước 2 — `.env` production (chi tiết: `3_env-production.md`)

```bash
# Sinh secret
openssl rand -hex 32     # → SECRET_KEY
openssl rand -base64 24  # → DB_PASSWORD
openssl rand -base64 24  # → MYSQL_ROOT_PASSWORD
openssl rand -base64 24  # → REDIS_PASSWORD
openssl rand -hex 24     # → TELEGRAM_WEBHOOK_SECRET

# Tạo .env — dán template đầy đủ từ 3_env-production.md mục 3.2, điền các giá trị vừa sinh
# + ANTHROPIC_API_KEY/GEMINI_API_KEY + TELEGRAM_BOT_TOKEN + domain thật
nano .env
chmod 600 .env

# Xác nhận không còn placeholder
grep -n "REPLACE_ME" .env && echo "❌ còn thiếu" || echo "✔ OK"
```

## Bước 3 — Build image (chi tiết: `2_docker-packaging.md`)

```bash
docker compose build app
```

Lần build đầu mất khoảng 5-10 phút (torch CPU wheel + sentence-transformers + tải model
embedding vào image) — theo dõi output, không có bước nào cần tương tác thủ công.

## Bước 4 — Migrate + seed dữ liệu (chi tiết: `4_data-seed-migrate.md`)

```bash
docker compose up -d mysql redis
docker compose ps   # đợi cả 2 "healthy"

# Tạo DB/user nếu chưa tự động (xem 4_data-seed-migrate.md mục 4.2)

# Alembic — migration đầu tiên
docker compose run --rm app alembic revision --autogenerate -m "initial schema"
cat alembic/versions/*_initial_schema.py   # review trước khi apply
docker compose run --rm app alembic upgrade head

# Seed dữ liệu mẫu
docker compose exec -T mysql mysql -u root -p"$(grep ^MYSQL_ROOT_PASSWORD .env | cut -d= -f2)" \
  pancharm_production < resources/migrate/seed.sql

# Đồng bộ ChromaDB
docker compose run --rm app python scripts/seed_vectordb.py
```

## Bước 5 — Start toàn bộ stack

```bash
docker compose up -d
docker compose ps          # cả 3 service "healthy"/"running"
docker compose logs app --tail=100 -f   # Ctrl+C khi thấy "LangGraph graph compiled and ready"
```

Kiểm tra health nội bộ (chưa qua Nginx):

```bash
curl -s http://127.0.0.1:8088/health | python3 -m json.tool
# Kỳ vọng: {"status": "healthy", "checks": {"mysql": "ok", "chromadb": "ok"}}
```

## Bước 6 — Reverse proxy + TLS (chi tiết: `5_reverse-proxy-tls.md`)

```bash
# Server block HTTP tạm để certbot xác thực
sudo tee /etc/nginx/sites-available/pancharm <<'EOF'
server { listen 80; server_name __YOUR_DOMAIN__; location / { return 200 "ok"; } }
EOF
sudo ln -s /etc/nginx/sites-available/pancharm /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d __YOUR_DOMAIN__ --redirect --agree-tos -m __YOUR_EMAIL__ --no-eff-email

# Ghi đè config đầy đủ (SSE/webhook/security headers) — copy nguyên khối từ
# 5_reverse-proxy-tls.md mục 5.3 vào /etc/nginx/sites-available/pancharm
sudo nano /etc/nginx/sites-available/pancharm
sudo nginx -t && sudo systemctl reload nginx
```

Xác nhận:

```bash
curl -s https://__YOUR_DOMAIN__/health | python3 -m json.tool
```

## Bước 7 — Xác nhận webhook Telegram tự đăng ký

Vì `TELEGRAM_WEBHOOK_BASE_URL` đã set trong `.env` từ Bước 2, và app đã start ở Bước 5 —
`adapter/setup.py` đã tự gọi `setWebhook` lúc startup. Nếu HTTPS/domain chưa sẵn sàng lúc đó
(vd bạn start app trước khi làm Bước 6), việc đăng ký chỉ log warning chứ không crash app —
restart lại app sau khi Bước 6 xong để đăng ký lại:

```bash
docker compose restart app
curl -s "https://api.telegram.org/bot$(grep ^TELEGRAM_BOT_TOKEN .env | cut -d= -f2)/getWebhookInfo" | python3 -m json.tool
```

## Bước 8 — Bảo mật bổ sung (chi tiết: `8_security-hardening.md`)

Làm **ngay sau** khi xác nhận app chạy ổn — đừng để cửa sổ "app đã public nhưng chưa
hardening" kéo dài:

- [ ] Khoá SSH root-login + password-login
- [ ] Ẩn `/docs`, `/redoc`, `/openapi.json` khỏi public (hoặc giới hạn theo IP)
- [ ] fail2ban cho SSH + Nginx
- [ ] Bật `unattended-upgrades`
- [ ] Xác nhận `docker compose ps` không có port nào bind `0.0.0.0` ngoài Nginx (80/443)

## Bước 9 — Backup + quy trình deploy về sau

- Cron backup: `4_data-seed-migrate.md` mục 4.7
- Quy trình deploy các lần sau (không phải lần đầu): `9_deploy-process.md`

## Checklist hoàn tất

- [ ] `https://__YOUR_DOMAIN__/health` trả `status: healthy`
- [ ] `docker compose ps` — 3 service, tất cả `healthy`, không service nào restart loop
- [ ] Telegram `getWebhookInfo` — `url` đúng domain, `last_error_message` trống
- [ ] Gửi thử tin nhắn tới bot Telegram → nhận được phản hồi từ MAS
- [ ] `sudo ufw status` — chỉ mở 22/80/443
- [ ] `.env` quyền `600`, không nằm trong `git status`
- [ ] Backup cron đã set (`crontab -l`)
