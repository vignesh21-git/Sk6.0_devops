# What's Built — Sk6.0

> **Last updated:** 2026-05-14
> **Branch:** master · **Commits:** 2 (infra + this Phase 0/1 work uncommitted as of writing)

Living record of what's actually working in the codebase. Update when a phase closes or a feature lands. Source of truth lives in the code; this file is the index.

See also: [ROADMAP.md](ROADMAP.md) · [GAPS.md](GAPS.md) · [BUGS.md](BUGS.md)

---

## ✓ Phase 0 — Foundation

Verified end-to-end on 2026-05-14.

### Core (`backend/app/core/`)
| File | What it provides |
|------|------------------|
| `config.py` | Pydantic Settings (env-driven, cached). Dev defaults match `docker-compose.dev.yml`. |
| `logging.py` | structlog — colored console in dev, JSON in prod. |
| `exceptions.py` | `DomainError` hierarchy (`NotFoundError`, `ConflictError`, `AuthenticationError`, `AuthorizationError`, `InvariantViolation`). 4 FastAPI handlers wrap every error in `{"error": {"code", "message", "details", "request_id"}}` + sets `X-Request-ID` header. |
| `security.py` | `hash_password`/`verify_password` (bcrypt). `create_access_token(user_id, role, jti)` → `(token, jti, expires_at)`. JWT HS256 / 24h. |

### Infrastructure (`backend/app/infrastructure/`)
| File | What it provides |
|------|------------------|
| `db/engine.py` | Async SQLAlchemy engine. `statement_cache_size=0` for pgbouncer transaction-pool safety. |
| `db/session.py` | `SessionFactory` + `get_session()` FastAPI dep. |
| `db/uow.py` | `UnitOfWork` async context manager. |
| `cache/redis_client.py` | Async Redis client with module-level connection pool. |
| `external/otp_gateway.py` | `OtpGateway` ABC + `DevStubOtpGateway` that logs OTP. Factory `make_otp_gateway()`. |

### Migrations
- `alembic.ini` + `migrations/env.py` (async-aware, pulls `DATABASE_URL` from app config)
- `migrations/script.py.mako` template
- `migrations/versions/2026_05_14_1230_0001_create_users_table.py` ← first migration (Phase 1)

### Verified
- `curl localhost:16800/health` → `{"status":"ok","db":"ok","redis":"ok"}`
- `make migrate` runs cleanly
- Hot-reload works on file save

---

## ✓ Phase 1 — Auth Slice

Verified end-to-end on 2026-05-14. **11/11 unit tests passing.**

### Domain (`backend/app/domain/`)
- `entities/user.py` — `User` dataclass with state machine. Methods: `register()`, `mark_phone_verified()`, `record_login()`.
- `value_objects/phone.py` — `Phone` VO. Normalizes `+91`/`91`/`0` prefixes. Validates Indian mobile (10 digits, starts with 6–9). Raises `InvariantViolation` on bad input.
- Enums: `UserStatus` (`pending`/`active`/`blocked`/`rejected`), `UserRole` (`user`/`admin`/`superadmin`).

### Application (`backend/app/application/`)
- `interfaces/repositories.py` — `UserRepository` ABC.
- `interfaces/services.py` — `SessionStore` and `OtpStore` ABCs + `SessionRecord` and `OtpRecord` DTOs.
- `use_cases/auth/`:
  - `register.py` — creates user (status=pending), generates OTP, sends via gateway.
  - `request_otp.py` — re-issues OTP for an existing phone.
  - `verify_otp.py` — verifies OTP, marks `phone_verified`, locks out after 5 failed attempts.
  - `login.py` — validates password + phone_verified + status, issues JWT, stores `jti` in Redis.
  - `logout.py` — revokes `jti` from Redis.
  - `_otp.py` — helper for generating numeric OTP codes.

### Infrastructure
- `db/models/base.py` — SQLAlchemy `DeclarativeBase`.
- `db/models/user.py` — `UserModel` (UUID PK, server-side `gen_random_uuid()`, CHECK constraints on status/role).
- `db/repositories/user.py` — `SqlAlchemyUserRepository` (entity ↔ model mapping).
- `cache/session_store.py` — `RedisSessionStore`. Keys: `session:{jti}` (TTL = JWT expiry) + `user_sessions:{user_id}` set for bulk revoke.
- `cache/otp_store.py` — `RedisOtpStore`. Keys: `otp:{phone}` + `otp_attempts:{phone}` with shared TTL.

### Presentation (`backend/app/api/v1/`)
| Endpoint | Method | Auth | What it does |
|----------|--------|------|--------------|
| `/api/v1/auth/register` | POST | none | Create user (pending), send OTP. → 201 |
| `/api/v1/auth/request-otp` | POST | none | Re-issue OTP for existing phone. |
| `/api/v1/auth/verify-otp` | POST | none | Verify OTP, set `phone_verified=true`. 5-attempt lockout. |
| `/api/v1/auth/login` | POST | none | phone+password → JWT. Rejects pending/blocked/rejected/unverified. |
| `/api/v1/auth/logout` | POST | Bearer | Revoke current `jti` from Redis. |
| `/api/v1/users/me` | GET | Bearer | Returns current user record. |

### DB schema (after migration `0001`)
- `users` (id UUID PK, phone unique, password_hash, full_name?, status, role, phone_verified, last_login_at?, created_at, updated_at)
- Indexes: `ix_users_phone` (unique), `ix_users_status`, `ix_users_last_login_at`
- CHECK constraints: `ck_users_status`, `ck_users_role`
- `pgcrypto` extension enabled

### Tests
- `tests/unit/auth/test_register.py` — 4 tests
- `tests/unit/auth/test_verify_otp.py` — 3 tests
- `tests/unit/auth/test_login.py` — 4 tests
- `tests/unit/fakes/` — `FakeUserRepository`, `FakeOtpStore`, `FakeSessionStore`, `FakeOtpGateway`
- `pyproject.toml` configures pytest-asyncio in auto mode

Run with: `docker exec sk6-api-1 sh -c "cd /app && pytest tests/unit -v"`

### Verified end-to-end flow
1. Register `9876543210` / `secret123` → 201
2. Read OTP from Redis (`docker exec sk6-redis redis-cli -a devpassword GET otp:9876543210`)
3. Verify OTP → `phone_verified=true`
4. Login before activation → 403 `USER_PENDING_APPROVAL` ✓
5. `UPDATE users SET status='active' WHERE phone='9876543210'`
6. Login again → 200 + JWT
7. `GET /users/me` with Bearer → 200 + full user
8. Logout → session revoked from Redis
9. `GET /users/me` same token → 401 `SESSION_REVOKED` ✓ (force-logout proven)

---

## DevOps / Infra (built before Phase 0)

Detailed in the parent [README.md](../README.md). Highlights:
- 11-container stack (nginx, 1× api, pgbouncer, postgres, redis, 2× celery, flower, rustfs, prometheus, grafana). All `127.0.0.1:16XXX` in dev. See [docker-compose.dev.yml](../docker-compose.dev.yml).
- Monitoring config (Prometheus, Grafana, Loki, Promtail, Alertmanager) — running but not yet wired to any app metrics.
- CI/CD GitHub workflows ([.github/workflows/ci.yml](../.github/workflows/ci.yml), [deploy.yml](../.github/workflows/deploy.yml)) — present, not exercised yet.
- Scripts: `provision.sh`, `deploy.sh`, `backup.sh` — present, not exercised yet.
