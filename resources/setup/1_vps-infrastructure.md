# 1. Chuẩn bị hạ tầng VPS

Guideline chi tiết để dựng một VPS trống thành máy sẵn sàng chạy Pancharm MAS. Áp dụng cho
**Ubuntu 22.04/24.04 LTS**, spec tham chiếu: **6 vCPU (Xeon E5 v2) / 8GB RAM / 60GB SSD**.

---

## 1.1. Chọn & khởi tạo VPS

- OS: Ubuntu 22.04 LTS hoặc 24.04 LTS (khuyến nghị — nhiều gói Docker/ứng dụng build sẵn cho
  Ubuntu hơn Debian thuần, dễ tra cứu khi gặp lỗi).
- Với spec 6 vCPU/8GB/60GB: đủ chạy app + MySQL + Redis Stack + Nginx cùng lúc (xem phân bổ
  tài nguyên chi tiết ở `2_docker-packaging.md`), nhưng **không dư nhiều** — tránh cài thêm
  service không cần thiết lên cùng VPS này (vd không cài thêm CI runner, không cài GUI).
- Ghi lại ngay: IP public, root password ban đầu (nhà cung cấp gửi qua email) — sẽ đổi/khoá
  ở bước hardening SSH.

## 1.2. Đăng nhập lần đầu & tạo user thường

Không dùng `root` để vận hành hàng ngày — tạo user riêng có quyền sudo:

```bash
ssh root@<VPS_IP>

adduser deploy
usermod -aG sudo deploy

# Copy SSH key của máy local sang user mới (chạy từ máy LOCAL, không phải trên VPS)
# nếu chưa có keypair: ssh-keygen -t ed25519 -C "pancharm-deploy"
ssh-copy-id deploy@<VPS_IP>

# Từ đây đăng nhập bằng user deploy, không dùng root nữa
ssh deploy@<VPS_IP>
```

Việc khoá hẳn SSH root-login + password-login được xử lý chi tiết ở
`8_security-hardening.md` — làm ngay sau khi xác nhận `deploy` đăng nhập bằng key thành công.

## 1.3. Cập nhật hệ thống & timezone

```bash
sudo apt update && sudo apt upgrade -y
sudo timedatectl set-timezone Asia/Ho_Chi_Minh
timedatectl status   # xác nhận NTP synchronized: yes
```

NTP sai giờ ảnh hưởng trực tiếp tới: JWT `exp` claim (core/security.py), chữ ký webhook
HMAC có timestamp (Zalo/Messenger), và log rotation theo mốc 00:00 (core/logger.py) — nên
luôn xác nhận `timedatectl status` báo `synchronized: yes` trước khi đi tiếp.

## 1.4. Tạo swap file

Với 8GB RAM và stack có torch/transformers/sentence-transformers, một swap file 2-4GB là
lưới an toàn cho các đợt tải cao điểm (vd nhiều request encode embedding cùng lúc, hoặc lúc
`docker build` biên dịch dependency) — không dùng làm RAM chính (SSD chậm hơn RAM nhiều),
chỉ để tránh OOM-kill đột ngột.

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Giảm swappiness — chỉ dùng swap khi thật sự cần, ưu tiên RAM tối đa trước
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

free -h   # xác nhận swap 4.0G xuất hiện
```

## 1.5. Cài Docker Engine + Docker Compose V2

Dùng script cài chính thức của Docker (không dùng gói `docker.io` trong apt repo mặc định
của Ubuntu — thường là bản cũ, thiếu Compose V2 plugin cần cho `deploy.resources.limits`
trong `docker-compose.yml` của project này):

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Cho phép user deploy chạy docker không cần sudo
sudo usermod -aG docker deploy
newgrp docker   # hoặc logout/login lại để group có hiệu lực

docker --version
docker compose version   # PHẢI là Compose V2 (subcommand "compose", không phải "docker-compose")
```

## 1.6. Cấu hình firewall cơ bản (UFW)

Chi tiết rule đầy đủ nằm ở `8_security-hardening.md`, nhưng cần bật UFW ngay từ bước setup
hạ tầng để không có cửa sổ hở nào giữa lúc cài Docker và lúc hardening xong:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Lưu ý quan trọng: **không** mở port 3306 (MySQL) hay 6379 (Redis) ra ngoài — docker-compose
của project đã bind 2 port này vào `127.0.0.1` (không public), UFW ở đây chỉ là lớp phòng
thủ thứ hai.

## 1.7. Layout thư mục deploy

```bash
sudo mkdir -p /opt/pancharm
sudo chown deploy:deploy /opt/pancharm
cd /opt/pancharm

git clone <URL_REPO_CUA_BAN> app
cd app
```

Từ đây, mọi lệnh ở các file guide tiếp theo (`2_docker-packaging.md`,
`4_data-seed-migrate.md`, ...) đều chạy trong `/opt/pancharm/app` (root của repo, nơi có
`Dockerfile`, `docker-compose.yml`, `.env`).

## 1.8. Cài Nginx + Certbot (cho bước 5)

Cài trước ở đây để bước `5_reverse-proxy-tls.md` chỉ cần viết config, không phải cài lại
từ đầu:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable nginx
```

## 1.9. Checklist trước khi sang bước đóng gói

- [ ] Đăng nhập được bằng user `deploy` + SSH key (chưa cần khoá root, làm ở bước 8)
- [ ] `timedatectl status` → `synchronized: yes`, timezone đúng
- [ ] `free -h` → thấy swap 4.0G
- [ ] `docker compose version` chạy được, không lỗi permission (không cần `sudo docker`)
- [ ] `sudo ufw status` → active, chỉ mở 22/80/443
- [ ] Domain đã trỏ A record về IP VPS này (cần thiết cho bước 5 — certbot xác thực qua HTTP-01)
- [ ] `/opt/pancharm/app` đã có source code (git clone thành công)

Xong bước này, sang `2_docker-packaging.md` để build image.
