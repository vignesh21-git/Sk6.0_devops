# Bugs & Issues — Sk6.0

> **Last updated:** 2026-05-14

Bugs we hit while building, what caused them, and how they were fixed. Open issues at the top, closed at the bottom. New bugs go to the top; once fixed, move to the **Resolved** section with date.

See also: [STATUS.md](STATUS.md) · [GAPS.md](GAPS.md)

---

## Open

### B-O1. `sk6-flower` reports `unhealthy` in `docker ps`
**Date noted:** 2026-05-14
**Symptom:** `make ps` shows `sk6-flower    Up (unhealthy)`.
**Reality:** Flower itself works — http://localhost:16555 loads, login admin/admin, "Connected to redis" in logs.
**Cause (suspected):** the healthcheck probe path in `docker-compose.yml` doesn't match the URL Flower actually serves (Flower is mounted under `/flower/` via `--url_prefix=flower`).
**Severity:** low (cosmetic, won't trigger Prometheus alerts in dev).
**Workaround:** none needed, ignore the flag.
**Fix scope:** one-line edit to the healthcheck URL in the base compose. Tracked in [GAPS.md G-13](GAPS.md#g-13-flower-healthcheck-flags-unhealthy).

---

### B-O2. `make rustfs-setup` hits wrong port
**Date noted:** 2026-05-14
**Symptom:** Will fail with connection refused if invoked.
**Cause:** Hardcoded `localhost:9000` in Makefile, but dev RustFS is on `localhost:16100` after the port reshuffle.
**Severity:** low (not invoked yet; not needed until Phase 3 recharge screenshots).
**Fix scope:** one line in `Makefile`. Tracked in [GAPS.md G-12](GAPS.md#g-12-make-rustfs-setup-uses-stale-port).

---

### B-O3. `version: "3.9"` warnings on every `docker compose` command
**Date noted:** 2026-05-14
**Symptom:** `WARN ... the attribute version is obsolete` printed every time you invoke compose.
**Cause:** Leftover Compose v1 spec; Compose v2 ignores `version:`.
**Severity:** cosmetic.
**Fix scope:** remove the `version:` line from `docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose.prod.yml`. Tracked in [GAPS.md G-14](GAPS.md#g-14-version-39-warnings-on-every-compose-command).

---

## Resolved

### B-R1. Mixed `docker-compose` (v1) vs `docker compose` (v2) in Makefile
**Date:** 2026-05-14
**Symptom:** `make ps`, `make logs`, `make shell` etc. failed with `docker-compose: No such file or directory`.
**Cause:** System has only the Compose v2 plugin (`docker compose`), but the Makefile used the legacy hyphenated binary for ~10 targets.
**Fix:** Replaced every `docker-compose` (binary) → `docker compose` (plugin) in `Makefile`. Took care not to touch the *filenames* `docker-compose.yml/.dev.yml/.prod.yml`.

---

### B-R2. `make down` only stopped the prod stack
**Date:** 2026-05-14
**Symptom:** Running `make dev-bg` followed by `make down` left the dev containers running.
**Cause:** `down` target passed only `-f docker-compose.yml -f docker-compose.prod.yml`.
**Fix:** Now passes all three overlay files plus `--remove-orphans` and the `disabled` profile.

---

### B-R3. PgBouncer / Postgres 16 SCRAM auth mismatch
**Date:** 2026-05-14
**Symptom:** App's `/health` returned `db: error: ProtocolViolationError`. PgBouncer logs: `cannot do SCRAM authentication: wrong password type`.
**Cause:** `edoburu/pgbouncer:latest` defaults to `AUTH_TYPE=md5`. PostgreSQL 16 requires `scram-sha-256`. PgBouncer was sending md5 to Postgres; Postgres rejected it.
**Fix:** Added `AUTH_TYPE: plain` to pgbouncer's env in `docker-compose.dev.yml`. With the plain password stored, PgBouncer can complete a SCRAM challenge-response with Postgres.
**Note:** For production this needs revisiting — `plain` puts the cleartext password in pgbouncer's userlist. Acceptable on an internal Docker network in dev; production should use the SCRAM verifier or pgbouncer's `auth_user` + `auth_query` pattern.

---

### B-R4. `structlog.stdlib.add_logger_name` crashed with `PrintLoggerFactory`
**Date:** 2026-05-14
**Symptom:** `AttributeError: 'PrintLogger' object has no attribute 'name'` on every startup. App crashed before serving any request.
**Cause:** `add_logger_name` is a stdlib-bridge processor — it reads `logger.name`. But our config uses `PrintLoggerFactory`, which produces plain `PrintLogger` instances with no `.name` attribute.
**Fix:** Removed `structlog.stdlib.add_logger_name` from the processor chain. `structlog.processors.add_log_level` is enough.

---

### B-R5. `LoginUseCase` output couldn't be splatted into `LoginResponse`
**Date:** 2026-05-14
**Symptom:** `POST /auth/login` returned 500 with `AttributeError: 'LoginOutput' object has no attribute '__dict__'`. Login appeared broken in the e2e test.
**Cause:** `LoginOutput` is a `@dataclass(slots=True)`. Slots dataclasses don't have `__dict__`. The auth router was doing `return LoginResponse(**out.__dict__)`.
**Fix:** Construct `LoginResponse` explicitly with named fields in `app/api/v1/auth.py:login`. Could also use `dataclasses.asdict(out)`.
**Lesson:** if a dataclass uses `slots=True`, splat-from-`__dict__` won't work — use field-by-field or `asdict()`.

---

### B-R6. Bulk rename in Makefile broke compose file references
**Date:** 2026-05-14
**Symptom:** After `replace_all "docker-compose" → "docker compose"`, every `-f docker-compose.yml` became `-f docker compose.yml` (broken path with embedded space).
**Cause:** `replace_all` is greedy — it caught the binary name AND the filenames.
**Fix:** Followed up with three targeted replacements to restore `docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose.prod.yml`.
**Lesson:** when bulk-replacing a token that's also a filename prefix, do targeted edits or use a smarter search pattern.

---

### B-R7. First `make dev` failed: `env file .env not found`
**Date:** 2026-05-14
**Symptom:** `docker compose` errored out before starting anything.
**Cause:** `docker-compose.yml:16` has `env_file: .env`; Compose hard-fails if missing. `.env` is gitignored, so a fresh checkout doesn't have it.
**Fix:** Created `Sk6.0_devops/.env` with dev values that match the dev overlay's hardcoded credentials (`DB_PASSWORD=devpassword`, `REDIS_PASSWORD=devpassword`, etc.). Without matching values, pgbouncer/flower (which aren't overridden by the dev overlay) can't connect to their dependencies.
**Lesson:** onboarding note — first-time setup needs `cp .env.example .env`.
