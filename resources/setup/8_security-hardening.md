# 8. Bảo mật bổ sung (chi tiết)

Danh sách đầy đủ các lớp phòng thủ nên có trước khi coi VPS là "production". Đánh số theo
lớp (OS → mạng → Docker → app → dữ liệu → vận hành) để dễ audit định kỳ — không phải thứ tự
bắt buộc phải làm tuần tự, nhưng làm mục 8.1-8.3 sớm nhất có thể (trước khi mở app ra
internet ở bước 6 của `6_deployment-implementation.md`).

---

## 8.1. Hardening SSH

```bash
sudo nano /etc/ssh/sshd_config
```

Đổi/thêm các dòng sau:

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
AllowUsers deploy
ClientAliveInterval 300
ClientAliveCountMax 2
```

```bash
sudo systemctl restart sshd
```

**Trước khi đóng session SSH hiện tại**, mở 1 terminal MỚI thử đăng nhập lại
(`ssh deploy@<VPS_IP>`) để xác nhận vẫn vào được — nếu config sai, bạn có thể tự khoá mình ra
khỏi VPS. Chỉ đóng session cũ sau khi session mới xác nhận login thành công.

Đổi port SSH mặc định (22 → port khác) là tuỳ chọn — giảm được nhiễu log từ bot quét port
22 tự động, nhưng không phải lớp bảo mật thật sự (an ninh qua che giấu). Với
`PasswordAuthentication no` + fail2ban (mục 8.2) đã đủ chặn brute-force; chỉ đổi port nếu
muốn giảm nhiễu log.

## 8.2. fail2ban — SSH + Nginx

```bash
sudo apt install -y fail2ban

sudo tee /etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled = true
maxretry = 4
bantime = 3600
findtime = 600

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/pancharm.error.log
maxretry = 10
findtime = 60
bantime = 3600
EOF

sudo systemctl enable --now fail2ban
sudo fail2ban-client status
```

`nginx-limit-req` bắt IP nào liên tục dính `limit_req` (đã cấu hình ở
`5_reverse-proxy-tls.md`) và cấm hẳn ở tầng firewall (iptables) sau khi vượt ngưỡng —
mạnh hơn 429 đơn thuần vì chặn cả trước khi request chạm tới Nginx worker.

## 8.3. UFW — rà lại quy tắc

```bash
sudo ufw status verbose
```

Kỳ vọng CHỈ có: `22/tcp (OpenSSH) ALLOW`, `80/tcp ALLOW`, `443/tcp ALLOW`. Nếu thấy `3306`
hoặc `6379` xuất hiện — có ai đó (hoặc chính bạn lúc debug) đã `ufw allow` nhầm, gỡ ngay:

```bash
sudo ufw delete allow 3306
sudo ufw delete allow 6379
```

Xác nhận Docker không tự mở port qua UFW ngầm (Docker có lịch sử ghi thẳng iptables, bỏ qua
UFW) — kiểm tra thực tế bằng cách quét từ **máy khác** (không phải VPS):

```bash
# Chạy từ máy local, không phải trên VPS
nmap -Pn -p 3306,6379,8088 __YOUR_DOMAIN__
```

Cả 3 port phải là `filtered` hoặc `closed` — nếu `open`, quay lại `docker-compose.yml` xác
nhận cả 3 service đều bind `127.0.0.1:PORT:PORT` (không phải `PORT:PORT` — thiếu `127.0.0.1`
là expose ra toàn bộ interface, đây là lỗi cấu hình phổ biến nhất khi copy docker-compose từ
nơi khác).

## 8.4. X-Forwarded-For — điều kiện để rate limiter hoạt động đúng

Đã cấu hình 2 vế (nhắc lại vì đây là điểm dễ bỏ sót khi tự chỉnh sửa sau này):

1. Nginx: `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` (đã có ở mọi
   `location` trong `5_reverse-proxy-tls.md`).
2. Uvicorn: `--proxy-headers --forwarded-allow-ips=*` (đã có trong `CMD` của `Dockerfile`).

`--forwarded-allow-ips=*` chấp nhận header forwarded từ **bất kỳ** upstream nào gọi vào
uvicorn. Vì app chỉ bind `127.0.0.1:8088` (không public trực tiếp — xác nhận lại ở mục 8.3),
điều này an toàn: chỉ Nginx trên cùng máy mới gọi được vào app. Nếu sau này bạn thay đổi kiến
trúc (vd thêm reverse proxy khác, hoặc public thẳng cổng 8088), phải đổi giá trị này thành
IP cụ thể của proxy tin cậy, nếu không **request giả mạo có thể tự set X-Forwarded-For để
qua mặt rate limiter**.

## 8.5. Docker — thu hẹp bề mặt tấn công

- Container `app` đã chạy bằng user không phải root (`appuser`, uid 1000 — xem
  `Dockerfile`). Xác nhận: `docker compose exec app whoami` → phải ra `appuser`, không phải
  `root`.
- Không mount `/var/run/docker.sock` vào bất kỳ container nào (không có nhu cầu, và mount
  socket này = cấp quyền root trên host cho container đó).
- `docker-compose.yml` đã có `deploy.resources.limits` cho cả 3 service — chặn 1 container
  bị lỗi/tấn công (vd DoS qua request nặng) chiếm hết tài nguyên làm sập cả 2 service còn
  lại trên cùng VPS.
- Cập nhật base image định kỳ (không chỉ code app):
  ```bash
  docker compose pull mysql redis
  docker compose build --pull app
  docker compose up -d
  ```
- Dọn image/layer cũ tích tụ qua nhiều lần build (chiếm dần 60GB SSD):
  ```bash
  docker system df        # xem đang chiếm bao nhiêu
  docker image prune -af --filter "until=168h"   # xoá image không dùng, cũ hơn 7 ngày
  ```

## 8.6. Ẩn tài liệu API khỏi public

FastAPI mặc định expose `/docs` (Swagger UI), `/redoc`, `/openapi.json` công khai — lộ toàn
bộ schema request/response, tên field nội bộ, ra bất kỳ ai. Đã chặn ở tầng Nginx
(`5_reverse-proxy-tls.md` mục 5.3, `location ~ ^/(docs|redoc|openapi\.json)$` với `allow`
danh sách IP + `deny all`). Chọn 1 trong 2 hướng:

- **Xoá hẳn location đó** trong Nginx config → 3 route này rơi vào `location /` mặc định,
  vẫn bị chặn nếu bạn không set `allow`, hoặc **thêm code app** để tắt hẳn (an toàn nhất,
  không phụ thuộc cấu hình Nginx):
  ```python
  # main.py — chỉ bật /docs khi APP_VERSION có hậu tố "-dev", ví dụ
  app = FastAPI(
      ...,
      docs_url="/docs" if settings.APP_VERSION.endswith("-dev") else None,
      redoc_url=None,
      openapi_url=None if not settings.APP_VERSION.endswith("-dev") else "/openapi.json",
  )
  ```
  Đây là thay đổi code tuỳ chọn — không bắt buộc để deploy được, nhưng khuyến nghị nếu bạn
  không cần Swagger UI trên production (dùng ở local/staging là đủ).

## 8.7. Bí mật (secrets) — quy tắc xử lý

- `.env` luôn `chmod 600`, chỉ user `deploy` đọc được. Không bao giờ `cat .env` vào log,
  không paste nguyên file vào chat/ticket khi debug — che giá trị trước khi chia sẻ.
- Xác nhận `.env` chưa từng bị `git add` nhầm trong lịch sử:
  ```bash
  git log --all --full-history -- .env
  ```
  Nếu có kết quả → key trong đó coi như đã lộ (từng nằm trong git history dù đã xoá ở commit
  sau) — phải **rotate toàn bộ** API key/secret liên quan (Anthropic, Gemini, Telegram bot
  token, `SECRET_KEY`), không chỉ xoá khỏi git.
- Rotate `SECRET_KEY` = mọi JWT đã phát hành trước đó **mất hiệu lực ngay lập tức** (user
  phải đăng nhập lại) — cân nhắc thông báo trước nếu hệ thống đã có user thật.
- Không dùng lại giá trị mặc định trong `.env.example`/`resources/summary/*.md` cho bất kỳ
  môi trường nào ngoài local dev.

## 8.8. Vá lỗi tự động ở tầng OS

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Chọn "Yes" khi được hỏi bật cập nhật bảo mật tự động. Xác nhận đang chạy:

```bash
cat /etc/apt/apt.conf.d/20auto-upgrades
```

Chỉ bật auto-upgrade cho gói **security**, không bật full-upgrade tự động (tránh Docker/MySQL
tự nhảy major version không kiểm soát được lúc nửa đêm).

## 8.9. Quét lỗ hổng dependency định kỳ

```bash
docker compose run --rm app pip install pip-audit && docker compose run --rm app pip-audit -r requirements.txt
```

Chạy sau mỗi lần cập nhật `requirements.txt`, hoặc định kỳ hàng tháng — với stack có
`langchain`/`fastapi`/`cryptography` cập nhật thường xuyên, đáng để rà ít nhất trước mỗi lần
bảo vệ đồ án/demo trước hội đồng.

## 8.10. Sao lưu — mã hoá trước khi lưu ngoài VPS

Backup ở `4_data-seed-migrate.md` (mục 4.7) chứa dữ liệu user thật (email, lịch sử hội
thoại — `ConversationMessage`, `PsychStateLog`) — nếu đồng bộ backup ra ngoài VPS (rclone lên
cloud storage, v.v.), mã hoá trước:

```bash
gpg --symmetric --cipher-algo AES256 mysql_20260731.sql.gz
# tạo ra mysql_20260731.sql.gz.gpg — passphrase lưu riêng, KHÔNG cùng chỗ với file backup
```

## 8.11. Phát hiện bất thường tối thiểu

Không cần dựng hẳn stack observability cho quy mô 1 VPS — nhưng nên có 1 cron nhẹ cảnh báo
khi container crash-loop:

```bash
# /opt/pancharm/healthcheck-alert.sh — thêm vào crontab chạy mỗi 5 phút
#!/bin/bash
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/health)
if [ "$STATUS" != "200" ]; then
    echo "$(date) — /health trả $STATUS" >> /opt/pancharm/health-alerts.log
    # Tuỳ chọn: gửi qua Telegram bằng chính bot token của bạn, curl tới api.telegram.org/bot.../sendMessage
fi
```

## 8.12. Checklist tổng hợp bảo mật

- [ ] SSH: `PermitRootLogin no`, `PasswordAuthentication no`, login lại xác nhận OK trước khi
      đóng session cũ
- [ ] fail2ban chạy, `jail.local` có `sshd` + `nginx-limit-req`
- [ ] `ufw status` chỉ mở 22/80/443, xác nhận bằng `nmap` từ máy ngoài
- [ ] `docker compose exec app whoami` → `appuser`, không phải `root`
- [ ] `/docs`, `/redoc`, `/openapi.json` không public (hoặc đã tắt hẳn qua code)
- [ ] `.env` quyền `600`, chưa từng nằm trong git history
- [ ] `unattended-upgrades` bật cho security updates
- [ ] Backup có mã hoá nếu đồng bộ ra ngoài VPS
- [ ] `pip-audit` chạy sạch (không lỗ hổng mức HIGH/CRITICAL chưa xử lý)

## 8.13. Phát hiện phụ trong lúc rà code — cần bạn quyết định

`core/config.py` khai báo `REFRESH_TOKEN_EXPIRE_MINUTES: int = 30` — nhưng file
`.env.example` bản gốc (trước khi dọn) từng có `REFRESH_TOKEN_EXPIRE_DAYS=30`, gợi ý ý định
ban đầu là **30 ngày**, không phải 30 phút. Nếu đúng vậy, refresh token hiện tại hết hạn chỉ
sau 30 phút — user bị bắt đăng nhập lại rất thường xuyên. Đây không phải lỗi chặn deploy,
nhưng đáng kiểm tra lại `core/security.py`/`services/auth_service.py` xem giá trị này có
đang được dùng đúng ý đồ không trước khi đưa cho user thật dùng.
