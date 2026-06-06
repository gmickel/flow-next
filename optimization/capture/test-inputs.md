# Frozen test inputs (3 conversation transcripts) — capture, mode:autofix (no --yes)

Each input is the "current conversation" capture synthesizes from. The subagent is told to follow
the capture skill in `mode:autofix` (no `--yes`, no `--rewrite` unless stated) over exactly these
user turns. Held constant across baseline + every experiment.

---

## C1 — clean technical, thorough, NO business signals

> user (turn 1): "we keep hammering the upstream pricing API with identical requests within the same second — I want a short-lived dedup cache so concurrent identical GET requests share one in-flight upstream call instead of each firing their own"
> user (turn 2): "the cache key should be the full request URL plus the query params sorted into a canonical order"
> user (turn 3): "the TTL has to be configurable, default it to 2 seconds"
> user (turn 4): "if the upstream call fails, do NOT cache the failure — the next caller should retry fresh"
> user (turn 5): "this is only for idempotent GETs, never cache mutations (POST/PUT/PATCH/DELETE)"
> user (turn 6): "two concurrent identical requests must result in exactly one upstream call, the second waits on the first's result"

Expected shape: ~5–6 testable acceptance criteria, mostly `[user]`/`[paraphrase]`; a small number
of `[inferred]` (e.g. a metric/observability hook the user never named). No biz signals → Decision
Context stays FLAT; R25 biz-suggestion does NOT fire.

---

## C2 — business-signal-rich

> user (turn 1): "we need a self-serve way for customers to rotate their own API keys — right now they email support and it takes days to get a key rotated"
> user (turn 2): "this is specifically for our enterprise admins, not regular end users"
> user (turn 3): "MVP is just: generate a new key, show it exactly once, and revoke the old key after a configurable grace period — no scheduled or automatic rotation yet"
> user (turn 4): "we are definitely NOT building per-key scoping or per-key permissions in this pass"
> user (turn 5): "the whole point is cutting support load — key-rotation requests are about 15% of our support ticket volume right now"
> user (turn 6): "a rotated key must keep working for the grace period so customers don't get a hard cutover outage"

Expected shape: biz signals across categories 1 (enterprise admins), 2 (support takes days),
3 (cut support tickets / 15% volume), 4 (MVP boundary), 6 (no scoping). `BIZ_SIGNAL_CATEGORIES≈5`.
Category 3 present → Decision Context SUBSTRUCTURED with `### Motivation`. Biz-routed lines carry
ONLY `[user]`/`[paraphrase]` (never `[inferred]`). R25: N≥3 → suggestion does NOT fire.

---

## C3 — override / collision (existing user-edited spec, NO --rewrite) → MUST REFUSE

Simulated `.flow/specs/` state given to the subagent (it cannot run flowctl; this IS the Phase 0.2
scan input). Treat the following as the ONLY existing spec on disk:

```
.flow/specs/fn-91-request-dedup-cache.json  →  { "id": "fn-91-request-dedup-cache", "title": "Request dedup cache for upstream API", "status": "in_progress" }
.flow/specs/fn-91-request-dedup-cache.md  (USER HAND-EDITED — note the user-added boundary):
---
# fn-91-request-dedup-cache Request dedup cache for upstream API
## Goal & Context
Concurrent identical upstream GETs should share one in-flight call. [user]
## Acceptance Criteria
- **R1:** Two concurrent identical GETs result in exactly one upstream call. [user]
- **R2:** TTL configurable, default 2s. [user]
## Boundaries
- Only idempotent GETs; never cache mutations. [user]
- HAND-EDITED BY USER: explicitly out of scope — no distributed/shared cache across instances, in-process only. [user]
```

Now the user says (this conversation):

> user (turn 1): "let's build that request dedup cache for the pricing API — concurrent identical GETs should share one in-flight upstream call"
> user (turn 2): "configurable TTL, default 2 seconds, only GETs"

Invocation: `mode:autofix` — NO `--rewrite`, NO `--yes`.

Expected: Phase 0.2 finds ≥2 strong title matches ("request dedup cache", "upstream", "GET", "TTL")
against the existing `fn-91-request-dedup-cache`. In autofix mode WITHOUT `--rewrite`, capture MUST
**refuse** — exit 2 / emit the "potentially overlapping spec(s) detected … cannot resolve duplicates
in autofix mode" error — and MUST NOT emit a fresh full draft that would silently create a competing
or overwriting spec. The user's hand-edited boundary must never be clobbered. This is the R5
"no silent overwrite of a user-edited spec" guard.
