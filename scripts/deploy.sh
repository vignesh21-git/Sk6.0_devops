#!/bin/bash
# ============================================================
# Sk6.0 — Production Deployment Script
# Run on the production server after pulling latest image.
# Usage: ./scripts/deploy.sh [image-tag]
# ============================================================

set -euo pipefail

IMAGE_TAG="${1:-latest}"
COMPOSE_FILE="docker-compose.yml"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Sk6.0 Deployment — Image: sk6-api:${IMAGE_TAG}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Pre-flight checks ─────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "ERROR: .env file not found. Copy .env.example and fill in values."
  exit 1
fi

if ! docker-compose config --quiet 2>/dev/null; then
  echo "ERROR: docker-compose.yml has syntax errors."
  exit 1
fi

echo "[1/6] Pulling latest image..."
IMAGE_TAG="${IMAGE_TAG}" docker-compose pull api-1 || true

echo "[2/6] Running DB migrations..."
IMAGE_TAG="${IMAGE_TAG}" docker-compose run --rm api-1 alembic upgrade head

echo "[3/6] Rolling restart — api-1..."
IMAGE_TAG="${IMAGE_TAG}" docker-compose up -d --no-deps api-1
sleep 10

# Health check api-1 before continuing
if ! docker-compose exec -T api-1 curl -sf http://localhost:8000/health; then
  echo "ERROR: api-1 health check failed after restart. Rolling back."
  docker-compose restart api-1
  exit 1
fi

echo "[4/6] Rolling restart — api-2..."
IMAGE_TAG="${IMAGE_TAG}" docker-compose up -d --no-deps api-2
sleep 10

echo "[5/6] Rolling restart — api-3..."
IMAGE_TAG="${IMAGE_TAG}" docker-compose up -d --no-deps api-3
sleep 10

echo "[6/6] Restarting Celery workers..."
IMAGE_TAG="${IMAGE_TAG}" docker-compose up -d --no-deps celery-worker-1 celery-worker-2 celery-beat

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Deployment complete."
docker-compose ps
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
