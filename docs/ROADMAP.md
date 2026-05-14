# Phase Plan & Roadmap — Sk6.0

> **Last updated:** 2026-05-14
> **Client:** Skathi agency · **Deadline:** 2026-06-30 · **Today:** 2026-05-14

5 two-week sprints, ~10 weeks total. Currently in **Sprint 2** (4–17 May).

See also: [STATUS.md](STATUS.md) · [GAPS.md](GAPS.md)

---

## Sprint summary

| Sprint | Dates | Theme | Status |
|--------|-------|-------|--------|
| 1 | 20 Apr – 3 May | Foundation (infra + backend skeleton) | infra done, app skeleton **caught up in Sprint 2** |
| **2** | **4 – 17 May** | **Auth + Wallet** | **descoped 2026-05-14 — see below** |
| 3 | 18 – 31 May | Lottery, draws, cart, settlement, results, reports | not started |
| 4 | 1 – 14 Jun | Admin app + iOS TestFlight | not started |
| 5 | 15 – 30 Jun | Load test (k6), security review, production cutover 30 Jun | not started |

---

## Sprint 2 — Descope (decided 2026-05-14)

Original Sprint 2 deliverables (OTP signup, login, wallet, recharge, withdrawal) require ~7–8 days of focused work; 3 days remaining at decision time. **Recharge and Withdrawal submission slip to Sprint 3.**

### In scope (Phases 0 / 1 / 2)

| Phase | Status | What it delivers |
|-------|--------|------------------|
| **0** Foundation | ✓ **complete** (2026-05-14) | Pydantic config, structlog, exception envelope, JWT+bcrypt, async SQLAlchemy, UoW, Redis client, OTP gateway interface + dev stub, Alembic init, enriched `/health`. |
| **1** Auth slice | ✓ **complete** (2026-05-14) | User domain + Phone VO + `users` table + 5 use cases + 5 auth endpoints + `/users/me` + 11 unit tests. End-to-end verified. |
| **2** Wallet reads | pending | Wallet domain + Money VO + `wallets`/`transactions` tables + `GET /wallet/balance` + `GET /wallet/history`. |

### Out of scope for Sprint 2 (moved to Sprint 3)

- Recharge submission (manual UPI + screenshot upload)
- Withdrawal submission (bank/UPI)
- Admin approval endpoint (currently a psql workaround — [GAPS.md G-1](GAPS.md#g-1-no-admin-approval-endpoint))

---

## Phase plans (detailed)

### Phase 0 — Foundation ✓

Goal: cross-cutting concerns and DB plumbing so feature work can start. ~1 day of work. See [STATUS.md](STATUS.md#-phase-0--foundation) for what landed.

---

### Phase 1 — Auth Slice ✓

Goal: end-to-end OTP signup + login + protected endpoint. ~3 days of work. See [STATUS.md](STATUS.md#-phase-1--auth-slice).

Bugs hit and fixed: [BUGS.md B-R3 through B-R7](BUGS.md#resolved).

---

### Phase 2 — Wallet Reads (next)

**Goal:** Authenticated user can fetch their wallet balance and paginated transaction history.

**Plan**
1. **Domain**: `Wallet` entity, `Money` value object (integer paise, never floats), `Transaction` entity (debit/credit, balance_before/after).
2. **DB migration**: `wallets` table (1:1 with users, `CHECK (balance >= 0)`), `transactions` table (cursor-friendly index on `(user_id, created_at DESC, id)`).
3. **Repos**: `WalletRepository`, `TransactionRepository` (read-only for now — debit/credit comes with recharge in Phase 3).
4. **Use cases**: `GetWalletBalance`, `ListTransactions` (cursor-paginated).
5. **Endpoints**: `GET /api/v1/wallet/balance`, `GET /api/v1/wallet/history?cursor=&limit=`.
6. **Wallet bootstrap**: a wallet row is created the first time `GetWalletBalance` is hit, OR on user activation. TBD — decide during build.
7. **Unit tests**: balance returns 0 for new users, history paginates correctly, blocked user → 403.

**Risk / known unknowns**
- Should wallet row creation be lazy (on first read) or eager (on user activation)? Lean lazy — fewer moving parts now, write-side comes with recharge.
- Money in API is integer paise per the design doc. Make sure Pydantic schema uses `int`, not `float`.

**Estimate:** ~1 day.

---

### Phase 3 — Sprint 3 (18 – 31 May)

Re-planned to absorb Sprint 2 slippage:

| Item | Origin | Est |
|------|--------|-----|
| Recharge submission (`POST /recharge/request` multipart + `/recharge/history`) | Sprint 2 slip | 2 days |
| Withdrawal submission (`POST /withdrawal/request`) | Sprint 2 slip | 1 day |
| Admin approval & block endpoints (`/admin/users/*`) | Sprint 3 original | 1 day |
| Recharge admin approval flow (`/admin/recharge/*`) | Sprint 3 original | 1 day |
| Withdrawal admin approval flow (`/admin/withdrawal/*`) | Sprint 3 original | 1 day |
| Audit log table + admin reads | Sprint 3 original | 1 day |
| DB `sessions` table + view-my-sessions endpoint | [GAPS G-3](GAPS.md#g-3-no-db-sessions-table) | 0.5 day |
| Password reset flow | [GAPS G-4](GAPS.md#g-4-no-password-resetchange-endpoints) | 0.5 day |
| Real zplusone OTP adapter | [GAPS G-2](GAPS.md#g-2-otp-gateway-is-a-dev-stub) | 0.5 day |

That's already ~9 days of work for a 10-working-day sprint. Originally Sprint 3 was also supposed to land the entire lottery domain (draws, bets, results, settlement). **Sprint 3 will need its own descope decision around 25 May.**

---

### Phase 4 — Sprint 4 (1 – 14 Jun)

Original scope: Admin app frontend, iOS TestFlight submission. If Sprint 3 carries lottery work, this sprint absorbs that.

To plan in detail closer to the sprint.

---

### Phase 5 — Sprint 5 (15 – 30 Jun, cutover)

- k6 load test (`backend/tests/load/draw-close.js`) — burst to 300 RPS at draw-close
- Security review (`make security-scan`: bandit + safety; pen test if budgeted)
- Production cutover (30 Jun deadline)

---

## How to re-plan

When a sprint slips, follow this pattern (used 2026-05-14 for Sprint 2):

1. Stop new feature work.
2. List remaining items honestly with day estimates.
3. Move tail to next sprint.
4. Update [STATUS.md](STATUS.md), this file, and a memory entry (`sk6-sprint2-scope.md` is the precedent).
5. Flag to client at next demo (per SOW §9.1 change process).
