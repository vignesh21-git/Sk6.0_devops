# Python Project Architecture

> **Pattern:** Clean Architecture (a.k.a. Hexagonal / Ports & Adapters / Onion)
> **Last updated:** 2026-05-14
> **Worked example:** this codebase (FastAPI + PostgreSQL + Redis + Celery)

A reusable architectural reference for Python projects. Tuned for transactional services with non-trivial business rules (money, multi-step workflows, multiple entry points). Lift the structure into any future project; only the contents change.

See also: [STATUS.md](STATUS.md) · [ROADMAP.md](ROADMAP.md)

---

## TL;DR

- Four concentric layers: **Domain → Application → Infrastructure / Presentation**.
- Dependencies point **inward only**. Inner layers know nothing about outer ones.
- Outer layers depend on **interfaces** the inner layers declare (Repository, Service ABCs).
- Concrete implementations are injected at the edge (FastAPI `Depends`).
- Tests use **fakes** for boundaries, not mocks.

**Fits:** transactional web apps, money/business-rule-heavy domains, long-lived projects, anything with multiple entry points (HTTP + background workers) sharing logic.
**Doesn't fit:** quick scripts, prototypes, pure-ML notebooks, plain CRUD with zero rules.

---

## Why this pattern for this kind of project

| Reality | What it forces |
|---------|----------------|
| FastAPI HTTP + Celery workers share use cases | Use cases can't depend on HTTP or task runners |
| Money & wallet invariants (`balance >= 0`, paise-only, idempotency) | Business rules live in one obvious place — the domain |
| Three persistence backends (Postgres, Redis, RustFS) | Each gets its own adapter; the rest of the code doesn't care |
| 10-week build, multi-year ops | Future-you (or a new dev) can locate code by purpose, not by accident |
| Tests need to be fast | No DB / Redis / HTTP needed for use-case tests; fakes are cheap |

---

## The four layers

```
                  ┌────────────────────────────┐
                  │  Presentation (HTTP / CLI) │
                  └─────────────┬──────────────┘
                                ▼
              ┌─────────────────────────────────┐
              │ Application (Use Cases)         │
              │  uses interfaces ↓              │
              └──────────┬──────────┬───────────┘
                         ▼          ▼
              ┌─────────────────┐  ┌────────────────────┐
              │ Domain          │  │ Infrastructure     │
              │ (pure Python)   │  │ (DB, cache, HTTP)  │
              └─────────────────┘  └────────────────────┘
                         ▲                  │
                         └──────────────────┘
                       Infrastructure imports
                       Domain entities (one-way)
```

### 1. Domain — innermost, zero outside deps

Pure Python. Entities, value objects, domain events, domain exceptions. No `import` from any framework, DB driver, HTTP library, or even your own outer layers.

- **Entities** — things with identity that change over time (`User`, `Wallet`, `Bet`)
- **Value objects** — immutable, equality-by-value, validated on construction (`Phone`, `Money`, `TicketNumber`)
- **Domain exceptions** — `InvariantViolation`, `NotFoundError` — never `HTTPException`

This project: [app/domain/entities/user.py](../backend/app/domain/entities/user.py), [app/domain/value_objects/phone.py](../backend/app/domain/value_objects/phone.py).

### 2. Application — use cases

Orchestration. One class per business action, with a single `execute(input) -> output`. Knows the domain. Talks to outer layers **only through interfaces** it itself declares (`UserRepository`, `SessionStore`, `OtpGateway`).

- ✗ Never imports FastAPI, SQLAlchemy, Redis, Celery
- ✓ Imports domain entities and the interfaces it owns

This project: [app/application/use_cases/auth/login.py](../backend/app/application/use_cases/auth/login.py), [app/application/interfaces/](../backend/app/application/interfaces/).

### 3. Infrastructure — concrete adapters

Where the technology lives. SQLAlchemy ORM models, Redis client, HTTP clients to third parties, Celery tasks. Implements the interfaces declared in Application. Maps domain entities to/from rows.

- ✗ Never contains business rules
- ✓ Can import Domain (to construct entities), Application (the interface to implement)

This project: [app/infrastructure/db/repositories/user.py](../backend/app/infrastructure/db/repositories/user.py), [app/infrastructure/cache/session_store.py](../backend/app/infrastructure/cache/session_store.py).

### 4. Presentation — the edge

HTTP routers, Pydantic request/response DTOs, dependency injection wiring. Translates HTTP → use-case input; use-case output → HTTP response. Installs global exception handlers.

- ✗ Never queries the DB directly
- ✗ Never holds a business rule
- ✓ Imports use cases and `Depends`-injects collaborators

This project: [app/api/v1/auth.py](../backend/app/api/v1/auth.py), [app/api/v1/deps.py](../backend/app/api/v1/deps.py).

---

## Canonical folder structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app + lifespan + router registration
│   ├── core/                    # cross-cutting (config, logging, security, exceptions)
│   ├── api/
│   │   └── v1/
│   │       ├── deps.py          # DI: get_current_user, get_user_repository, …
│   │       └── <feature>.py     # router per feature area
│   ├── schemas/                 # Pydantic request/response DTOs
│   ├── application/
│   │   ├── interfaces/          # repository & service ABCs (the "ports")
│   │   └── use_cases/
│   │       └── <feature>/       # one file per use case
│   ├── domain/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── events/              # (optional) domain events
│   │   └── exceptions.py
│   └── infrastructure/
│       ├── db/
│       │   ├── engine.py        # SQLAlchemy engine
│       │   ├── session.py       # session factory + FastAPI dep
│       │   ├── uow.py           # Unit of Work
│       │   ├── models/          # SQLAlchemy ORM declarative models
│       │   └── repositories/    # ORM-backed repository implementations
│       ├── cache/               # Redis client + Redis-backed stores
│       ├── external/            # third-party API adapters (OTP gateway, payment, …)
│       └── tasks/               # Celery app + task modules
├── migrations/                  # Alembic
└── tests/
    ├── unit/
    │   ├── fakes/               # in-memory implementations of each interface
    │   └── <feature>/           # use-case tests using fakes
    └── integration/             # real-DB, real-Redis tests
```

**Variation for smaller projects:** if a feature has only one use case, the folder per feature is overkill — flatten to `use_cases/<feature>.py`. Same for `domain/entities` if you have a handful of entities. The *layers* matter; the sub-folders are convention.

---

## Where does this code go? — decision tree

| If the code… | Lives in… |
|--------------|-----------|
| Defines a business concept (User, Money, Order) | `domain/entities/` or `domain/value_objects/` |
| Encodes a business rule with no I/O | `domain/` (method on an entity, or a value object) |
| Orchestrates multiple domain objects across one transaction | `application/use_cases/` |
| Defines an abstraction the use case needs (e.g. "store me a user") | `application/interfaces/` |
| Talks to Postgres / Redis / external API / S3 | `infrastructure/` |
| Parses an HTTP request body or serializes a response | `schemas/` (Pydantic) |
| Handles an HTTP route | `api/v1/` |
| Is configuration, logging setup, exception handlers, JWT helpers | `core/` |
| Is a background job (Celery task body) | `infrastructure/tasks/` |
| Is a CLI script | `scripts/` (outside `app/`) |

When in doubt, ask: *"What would have to change to swap Postgres for Mongo?"* The answer should be: only `infrastructure/db/`. If your domain or use case has to change, the rule was broken.

---

## Key patterns

### Use cases

One class per business action. Constructor takes collaborators; one method runs the action.

```python
class LoginUseCase:
    def __init__(self, *, users: UserRepository, sessions: SessionStore) -> None:
        self._users = users
        self._sessions = sessions

    async def execute(self, data: LoginInput) -> LoginOutput:
        ...
```

`LoginInput` / `LoginOutput` are plain dataclasses living next to the use case. Pydantic DTOs (which the router accepts/returns) translate to/from these at the edge.

> **Gotcha (we hit it):** `@dataclass(slots=True)` has no `__dict__`. You can't do `Response(**out.__dict__)` — construct field-by-field, or use `dataclasses.asdict(out)`. See [BUGS.md B-R5](BUGS.md#b-r5-loginusecase-output-couldnt-be-splatted-into-loginresponse).

### Repository pattern

An ABC in the application layer; concrete class in infrastructure. Repos return **domain entities**, not ORM rows.

```python
# application/interfaces/repositories.py
class UserRepository(ABC):
    @abstractmethod
    async def get_by_phone(self, phone: Phone) -> User | None: ...

# infrastructure/db/repositories/user.py
class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession): ...
    async def get_by_phone(self, phone: Phone) -> User | None:
        row = await self._session.execute(select(UserModel).where(...))
        return _to_entity(row) if row else None
```

The mapping function `_to_entity` is private to the repo. ORM models stay invisible outside `infrastructure/`.

### Unit of Work

Owns the transaction boundary. Use cases compose multiple repository operations under one UoW.

```python
async with UnitOfWork() as uow:
    user_repo = SqlAlchemyUserRepository(uow.session)
    wallet_repo = SqlAlchemyWalletRepository(uow.session)
    ...  # commit on success, rollback on exception
```

For simple read-only or single-write use cases, the FastAPI per-request session dependency (`get_db_session`) is enough. UoW shines when you need to coordinate writes.

### Value objects

Immutable, validated, equality-by-value. Replace primitives at boundaries — banishes "stringly-typed" bugs.

```python
@dataclass(frozen=True, slots=True)
class Phone:
    value: str
    def __post_init__(self) -> None:
        if not _PHONE_RE.match(normalized):
            raise InvariantViolation("Invalid Indian mobile number")
```

After this, `Phone("9876543210")` either succeeds or raises. The rest of the code can trust the value. Compare with: passing `str` everywhere and validating in 4 places (and forgetting in a 5th).

### Domain exceptions → HTTP

`DomainError` subclasses each declare their HTTP status; a single global handler converts them. Use cases raise domain exceptions; they never know about HTTP.

```python
class AuthorizationError(DomainError):
    code = "AUTHORIZATION_FAILED"
    http_status = 403
```

If you ever need to write `raise HTTPException(...)` from a use case, you've broken the rule — add a domain exception instead.

### Dependency injection

FastAPI's `Depends()` is the wiring point at the edge. Use cases receive everything via constructor injection. Tests inject fakes.

```python
# api/v1/deps.py
def get_user_repository(session: SessionDep) -> UserRepository:
    return SqlAlchemyUserRepository(session)
UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]

# api/v1/auth.py
@router.post("/login")
async def login(body, users: UserRepoDep, sessions: SessionStoreDep):
    return await LoginUseCase(users=users, sessions=sessions).execute(...)
```

For larger projects you may add a real container (e.g. `dependency-injector`); for most FastAPI apps the built-in `Depends()` is sufficient.

---

## Testing strategy

| Layer | Test type | What you mock/fake | Tools |
|-------|-----------|--------------------|-------|
| Domain | Unit | Nothing — pure objects | pytest |
| Application (use case) | Unit | Fakes for every interface (`FakeUserRepository`, …) | pytest, fakes in `tests/unit/fakes/` |
| Infrastructure (repo) | Integration | Real DB / Redis (testcontainers or compose) | pytest, sqlalchemy, testcontainers |
| API (HTTP) | Integration | Real app, real DB, fresh per test | pytest, httpx.AsyncClient |
| End-to-end | Smoke | Real running stack | bash + curl, k6 |

**Why fakes, not mocks:**
- A `Mock` lies — its `.get_by_phone()` returns whatever you wired up; nothing forces it to behave like a real repo.
- A `FakeUserRepository` implements the *same interface* with an in-memory dict. If you change the interface, the fake breaks at type-check time — you find out before tests run.
- Fakes are reusable across tests; mocks need re-setup per test.

This project: [tests/unit/fakes/user_repository.py](../backend/tests/unit/fakes/user_repository.py).

---

## Anti-patterns

| ✗ Don't | Why |
|---------|-----|
| `SQLAlchemy.select(...)` in a router | Router becomes coupled to ORM; use case skipped; testing harder |
| `HTTPException` raised from a use case | Couples business logic to HTTP; can't reuse in Celery workers |
| Domain entity importing from `sqlalchemy` | Breaks the dependency rule; can't unit-test the domain in isolation |
| Pydantic schemas used as the domain entity | Validation is presentational; mixes layers; serialization concerns leak |
| Service class with vague name (`UserService.do_things`) | Lose the "one class per use case" signal; rules drift |
| `float` for money | Floating-point rounding; never use floats for currency. **Always integer minor units (paise, cents)** |
| Mocks of internal collaborators in unit tests | Tests pass while the contract drifts; use fakes |
| Catching `Exception` to "make it pass" | Hides bugs; let `DomainError` flow to the global handler |
| Adding a `utils.py` | Becomes a dumping ground; put the function where its concept lives |
| `from app import *` | Hides what's actually used; breaks dependency analysis |

---

## When to bend the rules

- **Trivial CRUD**: if a feature really is "store this row, fetch this row" with no business rules, you can skip the application layer and let the router call the repo. *Add the use case the moment a rule appears* — don't defer until the codebase is full of half-applied conventions.
- **One-off scripts**: don't impose layers on a 50-line tool. `scripts/` directory, single file.
- **MVP / prototype**: a flat `models.py` + `routes.py` is fine if the goal is "validate this idea this week." Rewrite with layers when it survives 30 days in production.
- **Generated code**: Pydantic schemas auto-generated from OpenAPI specs, ORM models from `alembic --autogenerate` — these can live with looser structure since they're machine-rebuilt.

The rule is: *the conventions exist to keep mental load low across a multi-year codebase*. If applying a convention is slowing you down without making the code more changeable, reconsider.

---

## Tooling defaults

The picks below are pragmatic, not religious. Each replaces 2–3 older alternatives.

| Concern | Choice | Notes |
|---------|--------|-------|
| Web framework | FastAPI | Async, Pydantic-native, auto OpenAPI. Use Starlette directly only for non-HTTP ASGI. |
| ORM | SQLAlchemy 2.0 async | Industry default. Mature, typed. `asyncpg` driver under the hood. |
| Migrations | Alembic | Standard. Async env requires a custom `env.py` (see [migrations/env.py](../backend/migrations/env.py)). |
| Validation | Pydantic v2 | Already required by FastAPI. Use for HTTP DTOs and settings. |
| Settings | pydantic-settings | Reads env vars; cached via `lru_cache`. |
| Logging | structlog | Processor pipeline; JSON in prod, pretty in dev. |
| Background jobs | Celery (Redis broker) | Mature; alternatives are RQ (lighter) or Dramatiq. Use Celery when you need beat scheduling + multiple queues. |
| Cache / sessions / queue | Redis | Three jobs, one service. |
| Object storage | S3-compatible (RustFS in dev, S3/R2 in prod) | Abstract behind an interface; swap implementations. |
| Test runner | pytest + pytest-asyncio | Asyncio mode `auto` so you don't decorate every test. |
| Lint + format | ruff | Replaces black + isort + flake8 + pyupgrade in one tool. Fast. |
| Type check | mypy or pyright | Run in CI; treat type errors as build failures. |
| Password hash | bcrypt (or argon2) | Don't roll your own. |
| JWT | PyJWT | Simple. Avoid `python-jose` unless you need its extras. |
| HTTP client | httpx | Sync + async with the same API. Drop-in for `requests`. |
| Dependency mgmt | uv / poetry / pip-tools | Pick one. `requirements.txt` is fine for a single-target deploy. |

---

## Alternatives considered

| Architecture | Verdict |
|--------------|---------|
| **Django-style fat models** | Great for CRUD admin apps. Breaks down when business rules live across multiple models or call external systems. |
| **Flask + MVC** | Tight coupling to the framework. Same problems as Django at scale. |
| **Hexagonal Architecture** | Same idea, different vocabulary ("ports" = interfaces, "adapters" = infrastructure). Pick one term and stick with it. |
| **Full DDD** (bounded contexts, aggregates, domain event buses, ubiquitous language workshops) | Borrow the entity/VO/aggregate concepts; the rest is heavyweight unless you have a 20+ engineer org and a complex domain (insurance, healthcare, finance trading systems). |
| **Event Sourcing** | Powerful but the operational cost (event store, replays, projections, schema evolution) is steep. Not justified for typical CRUD-ish throughput. |
| **CQRS** | Separate read and write models. Useful when read/write paths diverge sharply. Premature for most apps; revisit if a hot read path starts dictating your write model. |
| **"Functional core, imperative shell"** | A leaner cousin of Clean. Works well in languages with strong sum types. In Python, you end up reinventing classes anyway — just use Clean. |
| **No architecture, just files** | Works for week-1 prototypes. Doesn't survive. |

---

## How to apply this to a new Python project

1. `pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy asyncpg alembic redis structlog bcrypt PyJWT pytest pytest-asyncio ruff mypy`
2. Create the folder structure above (empty `__init__.py` in each package).
3. Wire `app/core/config.py`, `app/core/logging.py`, `app/core/exceptions.py`, `app/core/security.py` first — these are stable across projects and can be near-copied from this repo.
4. Set up `app/infrastructure/db/engine.py`, `session.py`, and Alembic with the async `env.py`.
5. For the first feature: write the domain entity, then the use case (with fake repo, write the test), then the SQLAlchemy repo, then the router. In that order.
6. Add `docs/` early — `STATUS.md`, `GAPS.md`, `BUGS.md`, `ROADMAP.md`, `ARCHITECTURE.md`. Keep them current.

The cost of setting up these layers on day 1 is ~half a day. The cost of refactoring into them at month 6 is ~two weeks.

---

## Further reading

- *Clean Architecture* — Robert C. Martin
- *Architecture Patterns with Python* — Percival & Gregory (free at [cosmicpython.com](https://www.cosmicpython.com))
- *Domain-Driven Design* — Eric Evans (for entity / value object / aggregate concepts)
- *Implementing Domain-Driven Design* — Vaughn Vernon (practical guide)
- *Test-Driven Development with Python* — Harry Percival ("Obey the Testing Goat")
