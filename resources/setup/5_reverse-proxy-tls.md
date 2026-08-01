# 5. Reverse proxy & TLS

Dùng **Nginx cài trực tiếp trên host** (không containerize) làm reverse proxy trước app
container, + **Certbot** cấp/renew TLS tự động. Lý do chọn host Nginx thay vì thêm 1
container Nginx vào `docker-compose.yml`: certbot renew qua cron trên host đơn giản hơn, và
tách hẳn lớp TLS termination khỏi vòng đời container app (redeploy app không ảnh hưởng TLS).

Nginx + Certbot đã được cài ở bước `1_vps-infrastructure.md` (mục 1.8). App container đã
bind cổng `127.0.0.1:8088` (không public trực tiếp) — Nginx là cửa ngõ duy nhất ra internet.

---

## 5.1. Vì sao cấu hình này khác một reverse-proxy FastAPI thông thường

Có 3 điểm đặc thù của app này ảnh hưởng trực tiếp tới config Nginx:

1. **SSE streaming** — `GET /api/v1/chat/stream` (`api/v1/endpoints/base/chat_controller.py`)
   trả `StreamingResponse` với header `X-Accel-Buffering: no`. Nginx tôn trọng header này,
   nhưng để chắc chắn không có token nào bị buffer/delay, config bên dưới tắt hẳn
   `proxy_buffering` cho toàn route `/api/v1/`.
2. **Real client IP cho rate limiter** — `middleware/rate_limit_middleware.py` đọc
   `request.client.host`. Qua reverse proxy, giá trị này chỉ đúng nếu (a) Nginx forward
   `X-Forwarded-For` VÀ (b) uvicorn được chạy với `--proxy-headers` (đã cấu hình sẵn trong
   `Dockerfile`). Thiếu 1 trong 2 vế, mọi client sẽ bị coi là cùng 1 IP (127.0.0.1).
3. **Webhook Telegram cần response nhanh** — `webhook_controller.py` luôn trả 200 ngay (xử
   lý message ở `BackgroundTasks`), nhưng vẫn cần timeout đủ dài phòng trường hợp Telegram
   gửi burst nhiều update cùng lúc.

## 5.2. Lấy chứng chỉ TLS (chạy TRƯỚC khi viết config HTTPS)

Certbot plugin Nginx cần 1 server block HTTP đơn giản tồn tại trước để xác thực HTTP-01:

```bash
sudo tee /etc/nginx/sites-available/pancharm <<'EOF'
server {
    listen 80;
    server_name __YOUR_DOMAIN__;
    location / { return 200 "ok"; }
}
EOF

sudo ln -s /etc/nginx/sites-available/pancharm /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d __YOUR_DOMAIN__ --redirect --agree-tos -m __YOUR_EMAIL__ --no-eff-email
```

Certbot tự sửa file `pancharm` để thêm block HTTPS + redirect HTTP→HTTPS. Ta sẽ **ghi đè lại
toàn bộ file** ở bước 5.3 để thêm các tinh chỉnh riêng cho SSE/webhook, giữ nguyên phần
`ssl_certificate`/`ssl_certificate_key` certbot đã trỏ đúng đường dẫn.

## 5.3. Config Nginx đầy đủ

```bash
sudo tee /etc/nginx/sites-available/pancharm <<'EOF'
# Rate limit ở tầng Nginx — lớp phòng thủ NGOÀI, độc lập với RateLimitMiddleware trong app
# (middleware chỉ limit theo path đã vào tới app, cái này chặn sớm hơn, kể cả static/404).
limit_req_zone $binary_remote_addr zone=pancharm_rl:10m rate=60r/m;

upstream pancharm_app {
    server 127.0.0.1:8088;
    keepalive 32;
}

server {
    listen 80;
    server_name __YOUR_DOMAIN__;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name __YOUR_DOMAIN__;

    ssl_certificate     /etc/letsencrypt/live/__YOUR_DOMAIN__/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/__YOUR_DOMAIN__/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # HSTS — chỉ bật sau khi xác nhận HTTPS hoạt động ổn định (khó rollback vì trình duyệt cache)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 5m;

    # ── SSE streaming — /api/v1/chat/stream cần buffering off + read_timeout dài ──
    location /api/v1/chat/stream {
        proxy_pass http://pancharm_app;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding on;

        limit_req zone=pancharm_rl burst=20 nodelay;
    }

    # ── Webhook Telegram — cần trả nhanh, Telegram tự retry nếu timeout ──────
    location /api/v1/webhook/ {
        proxy_pass http://pancharm_app;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 5s;
        proxy_read_timeout 15s;

        # Không rate-limit webhook (Telegram gọi vào, không phải client cuối) —
        # HMAC/secret token verify đã có trong adapter (verify_webhook), đủ chặn giả mạo.
    }

    # ── Toàn bộ API còn lại ────────────────────────────────────────────────
    location /api/v1/ {
        proxy_pass http://pancharm_app;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 35s;   # ChatController.chat() tự timeout ở 30s, chừa buffer 5s

        limit_req zone=pancharm_rl burst=20 nodelay;
    }

    # Chặn hẳn Swagger UI/ReDoc công khai — chi tiết lý do: 8_security-hardening.md mục 8.6.
    # Đổi __YOUR_OFFICE_IP__ thành IP tĩnh của bạn, hoặc xoá cả block này nếu chấp nhận
    # không bao giờ xem /docs từ production (khuyến nghị mặc định).
    location ~ ^/(docs|redoc|openapi\.json)$ {
        allow __YOUR_OFFICE_IP__;
        deny all;
        proxy_pass http://pancharm_app;
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://pancharm_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    access_log /var/log/nginx/pancharm.access.log;
    error_log  /var/log/nginx/pancharm.error.log;
}
EOF

sudo nginx -t && sudo systemctl reload nginx
```

## 5.4. Xác nhận

```bash
curl -sI https://__YOUR_DOMAIN__/health
curl -s https://__YOUR_DOMAIN__/health | python3 -m json.tool

# Xác nhận real IP tới đúng app (không phải 127.0.0.1) — xem log app
docker compose logs app --tail=50 | grep RateLimit
```

## 5.5. Tự động renew TLS

Certbot cài sẵn systemd timer renew 2 lần/ngày — chỉ cần xác nhận:

```bash
sudo systemctl list-timers | grep certbot
sudo certbot renew --dry-run
```

## 5.6. Đăng ký webhook Telegram

Với `TELEGRAM_WEBHOOK_BASE_URL=https://__YOUR_DOMAIN__` đã set trong `.env` (mục 3.2),
`adapter/setup.py` tự gọi `TelegramAdapter.register()` mỗi lần app khởi động — không cần gọi
API Telegram thủ công. Xác nhận webhook đã đăng ký đúng sau khi `docker compose up -d`:

```bash
curl -s "https://api.telegram.org/bot$(grep ^TELEGRAM_BOT_TOKEN .env | cut -d= -f2)/getWebhookInfo" | python3 -m json.tool
```

Kỳ vọng `"url": "https://__YOUR_DOMAIN__/api/v1/webhook/telegram/pancharm"` và
`"last_error_message"` trống. Messenger/Zalo bạn tự setup sau — không cần đụng gì thêm ở
Nginx/DNS cho 2 kênh đó vì cùng chung route `/api/v1/webhook/{platform}/{bot_name}`.

Xong bước này, sang `6_deployment-implementation.md` để chạy toàn bộ end-to-end.
