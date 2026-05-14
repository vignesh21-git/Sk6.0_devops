# Dev Port Mapping — Sk6.0

> **Last updated:** 2026-05-14
> **Source of truth:** [`docker-compose.dev.yml`](../docker-compose.dev.yml)
> **Block:** `127.0.0.1:16XXX` (Sk6-reserved; loopback-only)

The dev stack binds every host-facing port to `127.0.0.1` in the `16XXX` band so it never collides with other projects running on the same machine (RxBB / Frappe bench, system Redis, rxbb-kb stack, Mosaic). Use SSH port-forwarding from your laptop to reach these in a browser.

This file is a **backup reference** — if the compose file gets overwritten, you can rebuild the port section from here.

See also: [STATUS.md](STATUS.md) · [docker-compose.dev.yml](../docker-compose.dev.yml)

---

## Full port table

| Host (dev) | Container | Service | Web URL / CLI |
|------------|-----------|---------|----------------|
| `127.0.0.1:16080` | nginx :80 | Nginx (main entry) | http://localhost:16080 |
| `127.0.0.1:16800` | api-1 :8000 | FastAPI (direct) | http://localhost:16800/api/docs |
| `127.0.0.1:16678` | api-1 :5678 | debugpy remote debugger | attach IDE |
| `127.0.0.1:16432` | postgres :5432 | PostgreSQL 16 | `psql -h localhost -p 16432 -U sk6 sk6` |
| `127.0.0.1:16379` | redis :6379 | Redis 7 | `redis-cli -h localhost -p 16379 -a devpassword` |
| `127.0.0.1:16555` | flower :5555 | Celery Flower | http://localhost:16555 (admin/admin) |
| `127.0.0.1:16300` | grafana :3000 | Grafana | http://localhost:16300 (admin/admin) |
| `127.0.0.1:16090` | prometheus :9090 | Prometheus | http://localhost:16090 |
| `127.0.0.1:16100` | rustfs :9000 | RustFS S3 API | `aws --endpoint-url http://localhost:16100 …` |
| `127.0.0.1:16101` | rustfs :9001 | RustFS Console | http://localhost:16101 |

PgBouncer (port 6432) and Postgres (5432) talk only over the internal Docker network — Postgres is *also* exposed on `:16432` for tools like DBeaver. The app connects via PgBouncer internally.

---

## SSH tunnel from your laptop

```bash
ssh \
  -L 16080:127.0.0.1:16080 \
  -L 16800:127.0.0.1:16800 \
  -L 16300:127.0.0.1:16300 \
  -L 16432:127.0.0.1:16432 \
  -L 16379:127.0.0.1:16379 \
  -L 16555:127.0.0.1:16555 \
  -L 16090:127.0.0.1:16090 \
  -L 16100:127.0.0.1:16100 \
  -L 16101:127.0.0.1:16101 \
  <host>
```

Then open `http://localhost:16080`, `http://localhost:16800/api/docs`, etc., in your browser.

---

## Why these specific ports

| Other project / system | Their ports | Sk6 stays clear by… |
|------------------------|-------------|---------------------|
| Frappe `bench start` (RxBB) | `8000` (web), `9000` (socketio), `6787` (file watcher), `11000` (redis_queue), `13000` (redis_cache) | API on `16800`, not 8000 |
| System Redis | `6379` | Sk6 Redis on `16379` |
| rxbb-kb Caddy | `80`, `443` (on 0.0.0.0) | Sk6 only binds 127.0.0.1, never 80/443 |
| rxbb-kb Postgres | `5433` | Sk6 Postgres on `16432` |
| rxbb-kb Streamlit / MCP | `8501`, `9876`, `9877` | Sk6 uses 16XXX block |
| Mosaic daemon | `8765` | Sk6 uses 16XXX block |

The `16XXX` band is also below the kernel's default ephemeral range (32768–60999), so it won't collide with auto-assigned sockets.

---

## How to restore if `docker-compose.dev.yml` is corrupted or reverted

The dev compose `ports:` section is the only place each binding is set. If a merge or a manual edit blows it away, the exact lines are:

```yaml
  api-1:
    ports:
      - "127.0.0.1:16800:8000"   # Direct API access for testing
      - "127.0.0.1:16678:5678"   # debugpy remote debugger

  flower:
    ports:
      - "127.0.0.1:16555:5555"   # Direct Flower UI access

  pgbouncer:
    environment:
      DB_PASSWORD: devpassword
      AUTH_TYPE: plain           # Postgres 16 SCRAM workaround — see BUGS.md B-R3

  postgres:
    ports:
      - "127.0.0.1:16432:5432"

  redis:
    ports:
      - "127.0.0.1:16379:6379"

  rustfs:
    ports:
      - "127.0.0.1:16100:9000"   # S3 API
      - "127.0.0.1:16101:9001"   # Web console

  grafana:
    ports:
      - "127.0.0.1:16300:3000"
    environment:
      GF_SERVER_ROOT_URL: "http://localhost:16300"

  prometheus:
    ports:
      - "127.0.0.1:16090:9090"

  nginx:
    ports:
      - "127.0.0.1:16080:80"
```

Or recover from git: `git checkout HEAD -- docker-compose.dev.yml` (this commit `feature/phase-1-auth-slice` is the first place the 16XXX block exists).

---

## Production note (not yet applied)

Production keeps `0.0.0.0:80` and `0.0.0.0:443` on Nginx (via [`docker-compose.prod.yml`](../docker-compose.prod.yml)) — those are the only public ports. Everything else stays on the internal Docker network or `127.0.0.1`. Don't carry the `16XXX` block into prod; it's a dev-only convention.
