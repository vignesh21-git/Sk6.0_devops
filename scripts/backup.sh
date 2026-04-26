#!/bin/bash
# ============================================================
# Sk6.0 — PostgreSQL Backup Script
# Add to cron: 0 2 * * * /opt/sk6/scripts/backup.sh
# ============================================================

set -euo pipefail

BACKUP_DIR="/opt/sk6/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/sk6_${DATE}.sql.gz"
RETAIN_DAYS=7

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting backup..."

docker-compose exec -T postgres pg_dump \
  -U sk6 \
  -d sk6 \
  --no-owner \
  --no-acl \
  --verbose \
  | gzip > "${BACKUP_FILE}"

echo "[$(date)] Backup written: ${BACKUP_FILE} ($(du -h ${BACKUP_FILE} | cut -f1))"

# Prune old backups
find "${BACKUP_DIR}" -name "sk6_*.sql.gz" -mtime +${RETAIN_DAYS} -delete
echo "[$(date)] Old backups pruned (kept last ${RETAIN_DAYS} days)."

echo "[$(date)] Backup complete."
