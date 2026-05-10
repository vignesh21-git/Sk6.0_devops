# Sk6.0 — Lottery Platform

A lottery platform (Web + Android + iOS) built on FastAPI, PostgreSQL, Redis, and Celery. The entire backend stack runs in Docker Compose. Nginx load-balances across API replicas in production.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Services](#services)
- [Backend Code Architecture](#backend-code-architecture)
- [Docker Compose Files](#docker-compose-files)
- [Development](#development)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Database](#database)
- [Business Domain](#business-domain)
- [Make Commands](#make-commands)

---

## Architecture Overview

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Nginx (80/443 in prod, 8080 in dev)                        │
│  TLS 1.3 termination · least_conn load balancing            │
│  Rate limiting · gzip · security headers                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┼───────────┐
           ▼           ▼           ▼
       api-1:8000  api-2:8000  api-3:8000   ← FastAPI + Gunicorn/Uvicorn
           │           │           │
           └───────────┴───────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │  PgBouncer :6432      │  ← Connection pooler (transaction mode)
           │  1500 clients → 25    │    1500 client conns → 25 Postgres conns
           └───────────┬───────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │  PostgreSQL 16 :5432  │  ← Primary database
           └───────────────────────┘

           ┌───────────────────────┐
           │  Redis 7 :6379        │  ← Cache · JWT sessions · Celery broker
           └───────┬───────────────┘
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
celery-worker-1         celery-worker-2
(settlements, default)  (notifications, default)
       │
celery-beat  ← Scheduler (NEVER scale — duplicate triggers)

           ┌───────────────────────┐
           │  RustFS :9000         │  ← S3-compatible object storage
           │  /sk6-static          │    Screenshots · PDF reports
           │  /sk6-backups         │
           └───────────────────────┘

Monitoring stack (optional profile):
  Prometheus → Alertmanager → Telegram
  Promtail   → Loki → Grafana
```

---

## Services

| Container | Image | Purpose | Internal Port |
|---|---|---|---|
| `nginx` | nginx:1.25-alpine | Reverse proxy, TLS, rate limiting | 80 / 443 |
| `api-1/2/3` | sk6-api (custom) | FastAPI application replicas | 8000 |
| `pgbouncer` | edoburu/pgbouncer | DB connection pooler | 6432 |
| `postgres` | postgres:16-alpine | Primary relational database | 5432 |
| `redis` | redis:7-alpine | Cache, sessions, Celery broker | 6379 |
| `celery-worker-1` | sk6-api | Task worker (settlements, default) | — |
| `celery-worker-2` | sk6-api | Task worker (notifications, default) | — |
| `celery-beat` | sk6-api | Periodic task scheduler | — |
| `flower` | sk6-api | Celery monitoring UI | 5555 |
| `rustfs` | rustfs/rustfs | S3-compatible object storage | 9000 / 9001 |
| `certbot` | certbot/certbot | Auto TLS renewal (prod only) | — |
| `prometheus` | prom/prometheus | Metrics collection | 9090 |
| `grafana` | grafana/grafana | Dashboards and alerting UI | 3000 |
| `alertmanager` | prom/alertmanager | Alert routing → Telegram | 9093 |
| `loki` | grafana/loki | Log aggregation backend | 3100 |
| `promtail` | grafana/promtail | Log shipper (Docker → Loki) | — |

### Port Map (Dev)

| Service | Host Port | Notes |
|---|---|---|
| Nginx | 8080 | Proxy to API |
| FastAPI | 8000 | Direct access |
| FastAPI debugpy | 5678 | Remote debugger |
| PostgreSQL | 5432 | DBeaver / pgAdmin |
| Redis | 6379 | RedisInsight |
| RustFS S3 API | 9100 | `mc` / `aws s3` |
| RustFS Console | 9101 | Web UI |
| Grafana | 3000 | Dashboards |
| Prometheus | 9090 | Metrics |
| Flower | 5555 | Celery monitor |

### Port Map (Production)

| Service | Host Port | Notes |
|---|---|---|
| Nginx HTTP | 80 | Redirects to HTTPS |
| Nginx HTTPS | 443 | TLS 1.3 only |
| RustFS S3 API | 127.0.0.1:9000 | Localhost only (backup scripts) |
| RustFS Console | 127.0.0.1:9001 | Localhost only |
| All others | — | Internal Docker network only |

---

## Backend Code Architecture

The backend follows **Clean Architecture** (hexagonal/onion). Dependency direction is strictly outer → inner. The domain layer has zero imports from any other layer.

```
Presentation  →  Application  →  Domain
                                    ↑
                 Infrastructure  ───┘
```

### The Four Layers

| Layer | Location | Contains | Must Never |
|---|---|---|---|
| Presentation | `app/api/` | FastAPI routers, Pydantic schemas, auth deps | Contain business rules or DB queries |
| Application | `app/application/` | Use-case classes, DTOs, transaction coordination | Import FastAPI, HTTP concepts, or SQL |
| Domain | `app/domain/` | Entities, value objects, domain exceptions | Import anything from outer layers |
| Infrastructure | `app/infrastructure/` | SQLAlchemy models, repositories, Redis, Celery | Contain business rules |

### Folder Structure

```
backend/
├── app/
│   ├── main.py                        # FastAPI entry point
│   ├── core/
│   │   ├── config.py                  # Settings (pydantic-settings)
│   │   ├── security.py                # JWT helpers, password hashing
│   │   ├── exceptions.py              # Global error handlers
│   │   ├── logging.py                 # structlog configuration
│   │   └── container.py              # Dependency injection wiring
│   ├── api/v1/                        # PRESENTATION LAYER
│   │   ├── deps.py                    # Shared FastAPI dependencies
│   │   ├── auth.py                    # /auth/register, /auth/login
│   │   ├── users.py                   # /users/me
│   │   ├── wallet.py                  # /wallet/balance, /wallet/history
│   │   ├── recharge.py                # /recharge/request
│   │   ├── withdrawal.py              # /withdrawal/request
│   │   ├── draws.py                   # /draws/today, /draws/open
│   │   ├── bets.py                    # /bets (place, cart)
│   │   ├── results.py                 # /results
│   │   └── admin/                     # Admin-only routes
│   ├── schemas/                       # Pydantic request/response DTOs
│   ├── application/                   # APPLICATION LAYER
│   │   ├── interfaces/                # Abstract repo & service interfaces
│   │   └── use_cases/                 # Business use-cases per domain
│   ├── domain/                        # DOMAIN LAYER (zero deps)
│   │   ├── entities/                  # User, Wallet, Bet, Draw, Result
│   │   ├── value_objects/             # Phone, Money, TicketNumber
│   │   ├── events/                    # BetPlaced, ResultPublished
│   │   └── exceptions.py
│   └── infrastructure/                # INFRASTRUCTURE LAYER
│       ├── db/
│       │   ├── engine.py              # SQLAlchemy async engine
│       │   ├── uow.py                 # Unit of Work
│       │   ├── models/                # ORM models
│       │   └── repositories/          # Concrete repo implementations
│       ├── cache/
│       │   └── redis_client.py
│       ├── external/
│       │   ├── otp_gateway.py         # WhatsApp OTP via zplusone.in
│       │   └── pdf_generator.py       # ReportLab PDFs
│       └── tasks/                     # Celery
│           ├── celery_app.py
│           ├── scheduler.py           # Beat schedule
│           ├── draws.py               # close_draw, settle_results
│           ├── notifications.py
│           └── reports.py
├── migrations/
│   └── schema.sql                     # Full DDL
└── tests/
    ├── unit/                          # Fake repos, no DB
    ├── integration/                   # Real DB + API
    └── load/                          # k6 scripts
```

---

## Docker Compose Files

Three files work together — base + overlay pattern.

### `docker-compose.yml` — Base

- Defines **all services**, networks, volumes, resource limits, healthchecks
- **No host port bindings** (environment-agnostic)
- Never run alone

### `docker-compose.dev.yml` — Development overlay

Adds on top of base:
- Hot-reload uvicorn (`--reload`) on api-1
- `./backend` mounted as volume — live code edits, no rebuild
- Celery worker with `watchmedo` auto-restart
- All ports exposed on host for direct tool access
- Hardcoded dev credentials (`devpassword`, `devaccess`, etc.)
- Disables: api-2, api-3, celery-worker-2 (profile: disabled)
- Excludes: Certbot, Alertmanager, Loki, Promtail (too heavy for dev)

### `docker-compose.prod.yml` — Production overlay

Adds on top of base:
- Nginx binds `80:80` and `443:443`
- RustFS binds `127.0.0.1:9000/9001` for backup script access
- Activates `--profile production` (Certbot) and `--profile monitoring`

---

## Development

### Prerequisites

- Docker + Docker Compose v2
- Git

### First-time setup

```bash
git clone <repo-url>
cd Sk6

# .env already has dev defaults — nothing to change for dev
# Just start:
make dev
```

### Daily workflow

```bash
make dev          # Start stack (foreground, Ctrl+C to stop)
make dev-bg       # Start detached

make logs         # Tail all container logs
make logs s=api-1 # Tail specific service

make shell        # bash inside api-1 (run manage commands)
make dbshell      # psql inside postgres
make redis-cli    # redis-cli inside redis

make migrate      # Run pending Alembic migrations
make migrate-new  # Create new migration (prompts for message)
make migrate-down # Roll back one migration

make test         # pytest unit + integration with coverage
make test-unit    # Unit tests only
make lint         # ruff check + mypy

make down         # Stop all containers
```

### Accessing services in dev

| URL | Service |
|---|---|
| `http://localhost:8000/health` | API (direct) |
| `http://localhost:8080/api/v1/...` | API (via Nginx) |
| `http://localhost:8000/api/docs` | Swagger UI |
| `http://localhost:3000` | Grafana (admin / admin) |
| `http://localhost:9090` | Prometheus |
| `http://localhost:5555` | Flower (admin / admin) |
| `http://localhost:9101` | RustFS Console (devaccess / devsecret123) |

### Adding a new feature

1. Write the domain entity / value object in `app/domain/`
2. Define the repository interface in `app/application/interfaces/`
3. Implement the use-case in `app/application/use_cases/`
4. Implement the SQLAlchemy repository in `app/infrastructure/db/repositories/`
5. Add the FastAPI router in `app/api/v1/`
6. Wire it in `app/core/container.py`
7. Run `make migrate-new` to generate the DB migration
8. Write unit tests in `tests/unit/` (fake repos, no DB)

---

## Production Deployment

### Server provisioning (once)

Run on a fresh Ubuntu 22.04 LTS server as root:

```bash
bash scripts/provision.sh
```

This installs: Docker, docker-compose, UFW firewall (22/80/443 only), fail2ban, unattended-upgrades, mc CLI, kernel TCP tuning, file descriptor limits, cron jobs.

### First deploy

```bash
# On the server as deploy user:
cd /opt/sk6
git clone <repo-url> .

# Configure environment
cp .env.example .env
nano .env   # fill in all values

# Configure alertmanager
cp monitoring/alertmanager/alertmanager.yml.example \
   monitoring/alertmanager/alertmanager.yml
nano monitoring/alertmanager/alertmanager.yml

# Get TLS certificate
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot \
  certonly --webroot -w /var/www/certbot -d yourdomain.com
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx

# Start full stack
make prod

# Set up RustFS buckets (once)
make rustfs-setup
```

### Rolling deploy (CI/CD or manual)

```bash
./scripts/deploy.sh [image-tag]
```

Performs: migrate → health-check api-1 → restart api-1 → health-check api-2 → restart api-2 → ... → restart workers.

---

## Configuration

All config lives in `.env` at the project root. Copy `.env.example` to start.

| Variable | Description | Dev default |
|---|---|---|
| `DB_PASSWORD` | PostgreSQL password | `devpassword` |
| `REDIS_PASSWORD` | Redis password | `devpassword` |
| `SECRET_KEY` | JWT signing key | `dev-secret-key-...` |
| `DOMAIN` | Public domain name | `localhost` |
| `GRAFANA_PASSWORD` | Grafana admin password | `admin` |
| `RUSTFS_ACCESS_KEY` | RustFS access key | `devaccess` |
| `RUSTFS_SECRET_KEY` | RustFS secret key | `devsecret123` |
| `RUSTFS_BUCKET` | Static files bucket | `sk6-static` |
| `RUSTFS_BACKUP_BUCKET` | Backups bucket | `sk6-backups` |
| `FLOWER_USER` | Flower basic auth user | `admin` |
| `FLOWER_PASSWORD` | Flower basic auth password | `admin` |
| `IMAGE_TAG` | Docker image tag for deploys | `latest` |

---

## Monitoring

### Stack

```
Docker containers
      │
   Promtail       ← reads container JSON logs via Docker socket
      │
     Loki         ← stores and indexes logs (30-day retention)
      │
   Grafana        ← dashboards + log explorer
      │
 Prometheus       ← scrapes /metrics from all API replicas, Flower, RustFS, Loki
      │
Alertmanager      ← routes firing alerts → Telegram
```

### Accessing (production, IP-restricted to 10.0.0.0/8)

```
https://yourdomain.com/grafana/   ← Grafana
```

Use SSH tunnel for access from outside:
```bash
ssh -L 3000:localhost:3000 deploy@yourserver.com
# then open http://localhost:3000
```

### Alert severity tiers

| Severity | Repeat interval | Examples |
|---|---|---|
| `page` | 1 hour | Settlement task failed, wallet inconsistency |
| `critical` | 15 minutes | API down, DB down, disk >90% |
| `warn` | 6 hours | High latency, high error rate, CPU >85% |

### Key alerts to know

| Alert | What it means |
|---|---|
| `SettlementTaskFailed` | Draw result credit task failed — check Flower immediately |
| `WalletBalanceInconsistency` | `balance < 0` detected — critical, should never fire |
| `DrawCloseTaskMissed` | Beat didn't fire on schedule — check celery-beat |
| `ApiHighErrorRate` | >5% 5xx for 5 min — check api logs |
| `DiskSpaceCritical` | Disk >90% — clean backups or expand volume |

---

## Database

Full DDL is in `backend/migrations/schema.sql`. Migrations are managed by Alembic.

### Key tables

| Table | Purpose |
|---|---|
| `users` | Accounts; status: pending / active / blocked |
| `wallets` | Balance ledger — 1:1 with users |
| `sessions` | JWT session tracking; `jti` → Redis for instant revocation |
| `transactions` | Every money movement with `balance_before` / `balance_after` |
| `recharge_requests` | Manual UPI recharge lifecycle |
| `withdrawal_requests` | Withdrawal approval queue |
| `draws` | One row per scheduled draw instance |
| `bets` | User bet tickets |
| `results` | Published winning numbers (immutable once set) |
| `winners` | Reverse-index from result → winning bets |
| `audit_logs` | Immutable admin action log |

### Wallet transaction safety

Every balance change goes through three layers — never bypass any:

1. **SERIALIZABLE isolation** on the session
2. **`SELECT ... FOR UPDATE`** on the wallet row before any debit
3. **`CHECK (balance >= 0)`** DB constraint — rejects negative balance at DB level

> **PgBouncer caveat**: running in transaction pool mode. Never use `LISTEN/NOTIFY`, PostgreSQL advisory locks, or `SET LOCAL` in application code — these require session mode and will silently fail.

### Migrations workflow

```bash
# Apply pending migrations
make migrate

# Create new autogenerated revision
make migrate-new   # prompts: "Migration message: "

# Roll back one revision
make migrate-down

# Show migration history
make migrate-history
```

---

## Business Domain

### Draw schedule

Four daily draw slots. Betting closes automatically 5 minutes before draw time:

| Draw Time | Betting Closes | Draw Types |
|---|---|---|
| 1:00 PM | 12:55 PM | Dear-3, Kerala-4 |
| 3:00 PM | 2:55 PM | Dear-3, Kerala-4 |
| 6:00 PM | 5:55 PM | Dear-3, Kerala-4 |
| 8:00 PM | 7:55 PM | Dear-3, Kerala-4 |

- **Dear-3**: 3-digit draw. Bet types: Single, Double, Box.
- **Kerala-4**: 4-digit draw. Same bet types.
- **Jackpot**: Separate type with own betting rules.

All times are **Asia/Kolkata (IST)**. Stored as UTC internally.

### Result entry flow (2-step)

1. Admin enters winning number → system previews winners + total payout
2. Admin confirms → `settle_draw_result` Celery task credits winners atomically

Results are locked once published — no updates or deletes.

### User lifecycle

```
Register (OTP) → pending → admin approves → active
                                          ↘ admin rejects
active → admin blocks → blocked
```

Blocked users receive 403 on every authenticated request. Their Redis session key is deleted on block — effective within the very next request.

### Money rules

- All amounts are **integer paise** in the API (`50000` = ₹500.00). Never floats.
- Recharge: max ₹9,999 per request; transaction ID must be numeric (1–12 digits); duplicate IDs rejected.
- Recharge is manual UPI — user uploads screenshot, admin approves/rejects.
- Withdrawal: to saved bank account (IFSC + account number) or UPI ID.

### Authentication (JWT + Redis)

- Algorithm: HS256, expiry: 24 hours
- Every JWT carries: `sub` (user UUID), `role` (user/admin/superadmin), `jti` (session ID)
- On login: `session:{jti}` stored in Redis with TTL = JWT expiry
- On every request: JWT verified, then `jti` checked in Redis — if missing/revoked → 401

### RBAC

| Route | Roles |
|---|---|
| `/api/v1/auth/*` | Public |
| `/api/v1/users/me`, `/api/v1/wallet/*` | user, admin, superadmin |
| `/api/v1/bets/*` | user (not blocked) |
| `/api/v1/admin/*` | admin, superadmin |
| `/api/v1/admin/system/*` | superadmin only |

---

## Make Commands

```
make dev              Start full dev stack (hot-reload, foreground)
make dev-bg           Start dev stack detached

make prod             Start production stack with monitoring
make up               Alias for prod
make down             Stop all containers
make restart          Restart all containers

make monitoring       Start alertmanager + loki + promtail only

make logs             Tail logs from all containers
make logs s=api-1     Tail logs from specific service
make ps               Show container status

make migrate          Run Alembic migrations (inside api-1)
make migrate-new      Create new Alembic revision
make migrate-down     Roll back one revision
make migrate-history  Show migration history

make test             pytest unit + integration with coverage
make test-unit        Unit tests only
make test-load        k6 load test

make lint             ruff check + mypy
make security-scan    bandit + safety check

make shell            bash inside api-1
make dbshell          psql inside postgres (db: sk6, user: sk6)
make redis-cli        redis-cli inside redis

make worker-stats     Celery worker inspect stats
make worker-active    Celery worker active tasks

make build            Build production Docker image (no-cache)
make rustfs-setup     Create RustFS buckets (run once after first deploy)

make clean            Remove stopped containers (docker system prune)
make clean-volumes    ⚠ Delete all data volumes (DESTRUCTIVE)
```
