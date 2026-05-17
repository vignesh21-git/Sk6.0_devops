# Sk6.0 Living Docs

Up-to-date state of the project. These four files are the **first place** to look when picking up work — they describe what's real, what's missing, what broke and why, and what's planned.

| File | What it tracks |
|------|----------------|
| [STATUS.md](STATUS.md) | What's actually built and working right now. Authoritative over CLAUDE.md when they disagree. |
| [GAPS.md](GAPS.md) | Known gaps with workarounds and planned resolution. |
| [BUGS.md](BUGS.md) | Bugs encountered, root cause, fix. Open at top, resolved at bottom. |
| [ROADMAP.md](ROADMAP.md) | Sprint plan + per-phase deliverables. Re-planned 2026-05-14 (Sprint 2 descope). |
| [PORTS.md](PORTS.md) | Dev `127.0.0.1:16XXX` port map with restore instructions. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Clean-Architecture reference for Python projects (template — applies here and reusable elsewhere). |

## Conventions

- **Update on phase close.** When a phase finishes, update STATUS + ROADMAP. When a bug is hit, add to BUGS (open) then move to resolved when fixed.
- **Always datestamp.** Each entry should have a date so stale info is obvious.
- **Cross-link.** Use relative links between these four files (`[GAPS.md G-1](GAPS.md#g-1-...)`). Memory entries can link too.
- **Source of truth lives in the code.** These docs are the *index*. When in doubt, read the code.

## When to consult

| You want to… | Read |
|--------------|------|
| Know what features actually exist | STATUS |
| Know why something doesn't work / what's the workaround | GAPS |
| Avoid repeating a fix that was already done | BUGS |
| Decide what to build next | ROADMAP |
