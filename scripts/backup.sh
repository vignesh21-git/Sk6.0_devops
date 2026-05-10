#!/bin/bash
# ============================================================
# Sk6.0 — PostgreSQL Backup Script
# Dumps DB → gzip → local → RustFS (sk6-backups bucket).
# Add to cron: 0 2 * * * /opt/sk6/scripts/backup.sh
#
# Prerequisites:
#   mc alias set sk6rustfs http://localhost:9000 $RUSTFS_ACCESS_KEY $RUSTFS_SECRET_KEY
#   mc mb sk6rustfs/sk6-backups
# ============================================================

set -euo pipefail

# ── Config ──────────────────────────────────────────────────
BACKUP_DIR="/opt/sk6/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/sk6_${DATE}.sql.gz"
RETAIN_DAYS=7

RUSTFS_ALIAS="${RUSTFS_ALIAS:-sk6rustfs}"
RUSTFS_BACKUP_BUCKET="${RUSTFS_BACKUP_BUCKET:-sk6-backups}"

mkdir -p "${BACKUP_DIR}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ── Dump ────────────────────────────────────────────────────
log "Starting backup..."

docker-compose -f /opt/sk6/docker-compose.yml exec -T postgres pg_dump \
  -U sk6 \
  -d sk6 \
  --no-owner \
  --no-acl \
  | gzip > "${BACKUP_FILE}"

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
log "Local backup written: ${BACKUP_FILE} (${BACKUP_SIZE})"

# ── Upload to RustFS ─────────────────────────────────────────
if command -v mc &>/dev/null; then
  log "Uploading to RustFS (${RUSTFS_ALIAS}/${RUSTFS_BACKUP_BUCKET})..."
  mc cp --quiet \
    "${BACKUP_FILE}" \
    "${RUSTFS_ALIAS}/${RUSTFS_BACKUP_BUCKET}/$(basename ${BACKUP_FILE})"
  log "RustFS upload complete."

  # Prune RustFS copies older than RETAIN_DAYS
  mc rm --quiet --recursive --force \
    --older-than "${RETAIN_DAYS}d" \
    "${RUSTFS_ALIAS}/${RUSTFS_BACKUP_BUCKET}/" 2>/dev/null || true
  log "RustFS old backups pruned (kept last ${RETAIN_DAYS} days)."
else
  log "WARNING: mc not found — skipping RustFS upload. Run provision.sh to install mc."
fi

# ── Prune local copies ───────────────────────────────────────
find "${BACKUP_DIR}" -name "sk6_*.sql.gz" -mtime +${RETAIN_DAYS} -delete
log "Local old backups pruned (kept last ${RETAIN_DAYS} days)."

log "Backup complete."
