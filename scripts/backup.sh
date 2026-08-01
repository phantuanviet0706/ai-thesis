#!/bin/bash
# Chạy trên VPS tại /opt/pancharm/backup.sh (copy ra khỏi repo, KHÔNG chạy từ trong app/).
# Cron: 0 3 * * * /opt/pancharm/backup.sh >> /opt/pancharm/backup.log 2>&1
# Chi tiết: resources/setup/4_data-seed-migrate.md mục 4.7
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
