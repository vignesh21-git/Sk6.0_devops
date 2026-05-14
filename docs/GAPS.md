# Known Gaps & Deferred Work — Sk6.0

> **Last updated:** 2026-05-14

Things that exist as design intent or workaround but aren't fully built. Each gap has a workaround (when one exists) and a planned resolution. Keep this list short — close gaps or move them to backlog tickets.

See also: [STATUS.md](STATUS.md) · [BUGS.md](BUGS.md) · [ROADMAP.md](ROADMAP.md)

---

## Auth & user lifecycle

### G-1. No admin approval endpoint
Registered users land in `status=pending` and stay there until manually activated.

**Workaround (dev):**
```bash
docker exec sk6-postgres psql -U sk6 -d sk6 \
  -c "UPDATE users SET status='active' WHERE phone='9876543210';"
```

**Planned:** Sprint 3 — `POST /api/v1/admin/users/{id}/approve` and `/reject` endpoints, admin-only, write to `audit_logs`.

---

### G-2. OTP gateway is a dev stub
`DevStubOtpGateway` logs OTP to `api-1` stdout. No real WhatsApp/SMS dispatch.

**Workaround (dev):**
```bash
# Either tail logs:
make logs s=api-1 | grep otp_dispatched
# Or read straight from Redis:
docker exec sk6-redis redis-cli -a devpassword GET "otp:9876543210"
```

**Planned:** Sprint 2 close / Sprint 3 — real `ZplusoneOtpGateway` adapter behind the same `OtpGateway` interface. Needs zplusone API credentials from client. One-file swap in `app/infrastructure/external/otp_gateway.py:make_otp_gateway()`.

---

### G-3. No DB `sessions` table
The CLAUDE.md design lists a `sessions` table for audit/admin "show all my sessions" view. Currently only Redis-backed (`session:{jti}` keys). Force-logout works fine via Redis bulk revoke — this is purely an audit-trail gap.

**Planned:** Sprint 3 — DB write at login (insert row), Redis stays the fast path.

---

### G-4. No password reset / change endpoints
`/auth/reset-password` listed in CLAUDE.md but not yet built.

**Planned:** Sprint 3.

---

## Business features not yet built (Sprint 2 descope)

### G-5. Recharge submission
Originally scoped for Sprint 2; descoped on 2026-05-14. `POST /api/v1/recharge/request` (multipart UPI screenshot) + `/recharge/history`.

**Planned:** Sprint 3, first item.

---

### G-6. Withdrawal submission
Originally Sprint 2; descoped. `POST /api/v1/withdrawal/request` with bank/UPI fields.

**Planned:** Sprint 3, second item.

---

### G-7. All admin endpoints
Approve/reject signup, block user, wallet reset, recharge/withdrawal approval, audit log viewer.

**Planned:** Sprint 3 (after Recharge/Withdrawal).

---

### G-8. Lottery domain (draws, bets, results, settlement)
The "real" product. No domain entities, no `draws/bets/results` tables, no Celery tasks.

**Planned:** Sprint 4.

---

## Tests & quality

### G-9. No HTTP-layer / integration tests
Unit tests exercise use cases with fake repos. No tests that hit the FastAPI app with a real DB.

**Planned:** When test scaffolding stabilizes (likely Sprint 3) — `httpx.AsyncClient` against the app + a per-test transactional DB fixture.

---

### G-10. No load tests
`make test-load` target references `backend/tests/load/draw-close.js` which doesn't exist.

**Planned:** Sprint 5, ahead of cutover.

---

### G-11. No `make lint` / `make security-scan` real targets
Targets exist in Makefile but `ruff`/`mypy`/`bandit`/`safety` aren't installed in the image.

**Planned:** Phase 0.5 follow-up — add to `requirements.txt` (dev-only) and verify targets run.

---

## Tooling & ops

### G-12. `make rustfs-setup` uses stale port
Target hardcodes `localhost:9000` for the mc CLI alias. After our port shift, RustFS S3 API is on `localhost:16100` in dev. Target will fail.

**Fix scope:** one line in `Makefile`. Defer until we actually need a RustFS bucket (Sprint 3, recharge screenshots).

---

### G-13. Flower healthcheck flags "unhealthy"
Flower service itself works fine (http://localhost:16555 loads, `Connected to redis` in logs). The Compose healthcheck probes a path that Flower doesn't expose at that exact URL.

**Fix scope:** small, fix Compose `healthcheck` to target `/flower/healthcheck` (or similar working URL).

---

### G-14. `version: "3.9"` warnings on every compose command
Compose v2 ignores `version:` and warns. Cosmetic.

**Fix scope:** remove the `version: "3.9"` line from `docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose.prod.yml`.

---

### G-15. `.env` is gitignored but contains dev credentials
The dev `.env` we generated holds dev-only passwords. Anyone cloning the repo has to run `cp .env.example .env`. Worth noting in onboarding.

**Resolution path:** add to a future `ONBOARDING.md`.

---

## Docs

### G-16. CLAUDE.md describes design, not current state
The [Sk6.0_devops/CLAUDE.md](../CLAUDE.md) describes the *target* Clean Architecture layout in full detail. Most of those folders are now built (Phase 0+1), but some (`infrastructure/tasks/draws.py`, `infrastructure/external/pdf_generator.py`, admin routers) still don't exist. Future Claude sessions should consult [STATUS.md](STATUS.md) for what's *actually* there.

**Resolution path:** keep STATUS.md authoritative. Eventually we'll close the gap or split CLAUDE.md into "target design" + "current state" sections.

---

### G-17. `backend/migrations/schema.sql` is an empty placeholder
2-line comment file. CLAUDE.md mentions it as the "full DDL" reference. Currently irrelevant — Alembic versions are authoritative.

**Resolution path:** delete the file and remove the CLAUDE.md reference, OR populate it as a human-readable schema dump on a release cadence.
