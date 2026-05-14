# ============================================================
# Sk6.0 — Makefile
# Shortcuts for common dev and ops tasks.
# Usage: make <target>
# ============================================================

.PHONY: help dev prod up down logs ps migrate test lint build clean monitoring rustfs-setup

# ── Help ─────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  Sk6.0 Platform — Available Commands"
	@echo "  ─────────────────────────────────────"
	@echo "  make dev          Start full dev stack (hot-reload)"
	@echo "  make prod         Start production stack (incl. monitoring)"
	@echo "  make up           Alias for prod"
	@echo "  make monitoring   Start alertmanager + loki + promtail only"
	@echo "  make down         Stop all containers"
	@echo "  make rustfs-setup Create RustFS buckets (run once after first deploy)"
	@echo "  make logs         Tail logs from all containers"
	@echo "  make logs s=api-1 Tail logs from specific service"
	@echo "  make ps           Show container status"
	@echo "  make migrate      Run Alembic DB migrations"
	@echo "  make migrate-new  Create new Alembic revision"
	@echo "  make test         Run backend unit + integration tests"
	@echo "  make lint         Run ruff + mypy"
	@echo "  make build        Build production Docker image"
	@echo "  make shell        Open bash in api-1 container"
	@echo "  make dbshell      Open psql in postgres container"
	@echo "  make redis-cli    Open redis-cli in redis container"
	@echo "  make worker-stats Show Celery worker status"
	@echo "  make clean        Remove stopped containers and volumes"
	@echo ""

# ── Development ───────────────────────────────────────────────
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

dev-bg:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# ── Production ────────────────────────────────────────────────
prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile production --profile monitoring up -d

up: prod

monitoring:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile monitoring up -d alertmanager loki promtail

down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.prod.yml --profile production --profile monitoring --profile disabled down --remove-orphans

restart:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.prod.yml --profile production --profile monitoring restart

# ── RustFS bucket setup (run once after first deploy) ─────────
rustfs-setup:
	@echo "Setting up RustFS buckets..."
	mc alias set sk6rustfs http://localhost:9000 $${RUSTFS_ACCESS_KEY} $${RUSTFS_SECRET_KEY}
	mc mb --ignore-existing sk6rustfs/sk6-static
	mc mb --ignore-existing sk6rustfs/sk6-backups
	mc anonymous set download sk6rustfs/sk6-static
	@echo "RustFS buckets ready."

# ── Logs ──────────────────────────────────────────────────────
logs:
	docker compose logs -f $(s)

# ── Status ────────────────────────────────────────────────────
ps:
	docker compose ps

# ── Build ─────────────────────────────────────────────────────
build:
	docker compose build --no-cache api-1

# ── Database Migrations ───────────────────────────────────────
migrate:
	docker compose exec api-1 alembic upgrade head

migrate-new:
	@read -p "Migration message: " msg; \
	docker compose exec api-1 alembic revision --autogenerate -m "$$msg"

migrate-down:
	docker compose exec api-1 alembic downgrade -1

migrate-history:
	docker compose exec api-1 alembic history --verbose

# ── Testing ───────────────────────────────────────────────────
test:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml \
		exec api-1 pytest tests/unit tests/integration -v --cov=app --cov-report=term

test-unit:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml \
		exec api-1 pytest tests/unit -v

test-load:
	cd backend/tests/load && k6 run draw-close.js

# ── Linting ───────────────────────────────────────────────────
lint:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml \
		exec api-1 sh -c "ruff check app/ && mypy app/"

security-scan:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml \
		exec api-1 sh -c "bandit -r app/ && safety check -r requirements.txt"

# ── Shell Access ──────────────────────────────────────────────
shell:
	docker compose exec api-1 bash

dbshell:
	docker compose exec postgres psql -U sk6 -d sk6

redis-cli:
	docker compose exec redis redis-cli -a $${REDIS_PASSWORD}

# ── Celery ────────────────────────────────────────────────────
worker-stats:
	docker compose exec celery-worker-1 celery -A app.infrastructure.tasks.celery_app inspect stats

worker-active:
	docker compose exec celery-worker-1 celery -A app.infrastructure.tasks.celery_app inspect active

# ── Cleanup ───────────────────────────────────────────────────
clean:
	docker compose down --remove-orphans
	docker system prune -f

clean-volumes:
	docker compose down -v
	@echo "WARNING: All data volumes deleted."
