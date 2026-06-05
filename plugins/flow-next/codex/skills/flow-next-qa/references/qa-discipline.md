# QA discipline — the lean BRB borrow

This reference carries the QA discipline `/flow-next:qa` borrows from Ray Fernando's
`running-bug-review-board` (BRB) skill. It is deliberately **lean** — flow-next already
owns most of the surrounding machinery (the spec as intent, the bug memory track,
receipts, the make-pr R-ID table, fn-52 tracker-sync), so this is the discipline, not
the 18-reference port.

> The session-hygiene rules, persona-suffix discipline, write-path-first /
> one-tab-per-shard caution, and the YES/NO verdict + paste-ready-handoff discipline are
> adapted from Ray Fernando's `running-bug-review-board` skill (Apache-2.0) — see
> CHANGELOG. The **P0/P1/P2 taxonomy, evidence rules, reproduce-twice, and the
> never-downgrade-a-P0 rule** are the *other* half of the same borrow — they live in
> **[bug-filing.md](bug-filing.md)** (do not duplicate them here; cross-link).

## What this reference covers (and what it does NOT)

| In this reference | Elsewhere |
|-------------------|-----------|
| Session hygiene — 5 rules + persona suffixing | — |
| Write-path-first / one-tab-per-shard caution (a paragraph, not a coordinator) | — |
| YES/NO verdict + paste-ready handoff discipline | Receipt write: `workflow.md` §6.3 |
| P0/P1/P2 taxonomy + tie-break, evidence rules, reproduce-twice | **[bug-filing.md](bug-filing.md)** |
| Driver commands (viewport, screenshot, storage clear, auth) | fn-51 `flow-next-drive/references/` |

**Driving is fn-51's job, not this reference's.** QA never re-implements driving — it
reads fn-51's workflow + references and executes the universal flow itself. The concrete
commands referenced below (`set viewport`, `screenshot`, storage clear, `state save/load`)
all live in fn-51:

- `agent-browser set viewport W H`, `agent-browser screenshot …` — `flow-next-drive/references/commands.md`
- The universal flow per rung — `flow-next-drive/references/agent-browser.md`
- Auth / state persistence — `flow-next-drive/references/auth.md`
- Per-session isolation (`--session`) — `flow-next-drive/references/session-management.md`

This reference says *what discipline to apply*; fn-51 says *how to drive*.

---

## Session hygiene — the silent bug factory

The single biggest source of **false** QA failures is stale session state bleeding across
scenarios. The single biggest source of **real** bugs that ship is the same thing from a
real user's point of view. Tracking session hygiene serves both goals — it is the
highest-dividend borrow. Apply it religiously.

### The five hygiene rules

1. **Fresh user = fresh storage.** Before any "fresh user" / "no invite / no prior
 context" scenario, clear app-level storage. Cookies alone are not enough —
 `localStorage` and `sessionStorage` outlive a logout and silently poison the next run.
2. **One browser tab (session) per agent.** Two agents on a shared tab cause auth-provider
 rate-limits, session bleed, and false failures. With agent-browser, isolate via
 `--session <name>` (see fn-51 `session-management.md`); if your tooling cannot guarantee
 isolation, run scenarios **sequentially**, not in parallel.
3. **Cool-down between auth attempts.** Auth providers throttle. ~30s between sign-ups is a
 safe default (e.g. Clerk dev keys); check the provider's docs. On a 429 / "too many
 requests", **stop the scenario and mark BLOCKED** — do not retry-spam, the limit grows.
4. **Unique persona per scenario.** A fresh-user scenario needs a fresh email with a unique
 suffix (see below). Reusing an email that previously hit an OTP / verify failure leaves
 the provider in a stuck state and produces a false failure on the next run.
5. **Reset between role changes.** Switching member → admin mid-pass means a full sign-out
 + storage clear + tab reset — not just "click sign out". Cookies and SSR auth state lag.

### Pre-scenario hygiene checklist

Run before each scenario (copy into the run notes, check off as you go):

```
Scenario hygiene:
- [ ] Persona email unique to this scenario (suffix bumped if reusing a base persona)
- [ ] If "fresh user": cleared sessionStorage + localStorage + cookies
- [ ] If "fresh user": signed out of any prior auth session
- [ ] This agent is the only one on this browser session (--session isolated)
- [ ] Last auth attempt was > ~30s ago (provider rate-limit safety)
- [ ] Viewport set to the device under test (one desktop OR one mobile — see device matrix)
- [ ] Console capture ready (the failure evidence in bug-filing.md depends on it)
```

### Persona suffix discipline

Even when a provider has no explicit test mode, give every fresh-user scenario a unique,
collision-proof email. The pattern (`example.com` is IANA-reserved — never sends real mail):

```
qa-<persona>+run<MMDD>-<N>@example.com
```

| Scenario | Persona | Note |
|----------|---------|------|
| S1 (fresh signup) | `qa-fresh+run0605-1@example.com` | new |
| S3 (fresh signup) | `qa-fresh+run0605-2@example.com` | new — N bumped |
| S3 retry | `qa-fresh+run0605-3@example.com` | retry — **bump the suffix** |

Bumping the suffix on a retry guarantees you are not tripping over the provider's
stuck-state cache from the prior (failed) attempt. The `+run<MMDD>` segment avoids
collisions with personas from a **prior** QA pass on the same app.

### When hygiene itself reveals a bug

If, *with perfect hygiene*, the user-visible behavior still depends on prior session state
in a way the user cannot predict, **that is the bug** — file it (typically P1). The
canonical case: a user who opened an invite link, abandoned it, then later signs up at
`/sign-up` with no invite param is silently joined to the old group because the app falls
back to `sessionStorage` when the URL has none. Invisible from inspection; reproducible
only by acting like a returning real user with stale state. Capture the storage snapshot
**before** clearing it — that snapshot is the evidence (see [bug-filing.md](bug-filing.md)).

### Test accounts — ask, don't guess

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

When the repo does not document test accounts, **ask the user via `plain-text numbered prompt`** before writing scenarios that need auth — never guess credentials.

Undocumented means any of: auth provider dev mode, an admin account or permission to create one, the per-run email-suffix convention, any payment / 3rd-party test credentials. Offer to document the convention as part of the pass.
Never commit a password to the repo; record the email pattern + role, pass secrets via the
existing chat / vault. (Provider-specific fixtures — Clerk `424242`, Stripe `4242…`, etc. —
are out of scope for this lean borrow; reach for the provider's own docs when a flow needs
them.)

---

## Write-path-first / one-tab-per-shard caution

This is a **caution paragraph**, deliberately *not* a parallel-coordinator machine — v1 QA
runs scenarios sequentially with one host agent; the disjoint-shard coordination is out of
scope. The two lessons worth carrying from BRB's parallel runs:

- **Write-path-first.** When a later scenario depends on data an earlier scenario creates (a
 group, an org, a workspace, an invite), run the **write path first** so the shared
 artifact exists before any scenario that reads it. Record the created IDs / invite URLs in
 the run notes so a follow-on scenario reuses them instead of re-creating (and re-asserting)
 the same state.
- **One tab (session) per agent.** If you ever *do* fan scenarios out across agents, each
 gets its **own** isolated browser session (`--session`) and its **own** persona suffix
 (`+run<MMDD>-<shard>`). Sharing a tab is what causes "no sign-in attempt found", stolen
 OTPs, and wrong-account writes. If isolation can't be guaranteed, **stay sequential** —
 the fix for a stalled parallel run is to go sequential, not to relaunch in parallel.

A common parallel failure worth pre-empting even in sequential mode: a scenario reports PASS
but the backend shows nothing wrote (optimistic UI). For any **write path**
(create / update / delete), verify the server / DB row or API response — never trust the
UI's optimistic render. That write-side-effect check is part of the evidence discipline in
[bug-filing.md](bug-filing.md).

---

## The verdict — YES/NO + paste-ready handoff

Every pass ends with **one** decision a human can act on, grounded in captured evidence —
never in agent narration, never in reading the diff (R1: PASS is forbidden from source
inspection). The mechanics (the four-outcome `qa_outcome` matrix, the projection to the
Ralph-guard `verdict` enum, and the receipt JSON write) live in **`workflow.md` §6**; this
reference carries the *discipline* that the verdict must obey.

### The four-outcome verdict (discipline, not mechanics)

| Outcome | Means | Honesty rule |
|---------|-------|--------------|
| **SHIP** (YES) | Every derived scenario passed on the live app, **zero** open P0/P1, R-ID coverage complete for every UI-observable criterion | Requires captured live-app evidence per passing scenario — no evidence ⇒ not SHIP |
| **NEEDS_WORK** (NO) | Any open P0 or P1, **or** an uncovered UI-observable R-ID (`⚠️ no live scenario`) | A single open P0 = NO; **never** downgrade a P0 to keep it green (see bug-filing.md tie-break) |
| **BLOCKED** | No live deploy reachable, or no driver (incl. fn-51 degraded to the terminal manual rung) | **BLOCKED ≠ FAIL** — "no ship *claim* on a QA basis", not "the app is broken" |
| **NA** | The spec has no driveable user-visible AC (all backend / CLI / non-UI) | Live QA raises no objection — record *why* in `na_reason`; never invent a fake UI path |

Load-bearing honesty rules (these are *the* reason the verdict is trustworthy):

- **Incomplete R-ID coverage is NO, not YES.** A confident PASS over an uncovered criterion
 is the failure mode this whole skill exists to prevent.
- **SHIP rests on evidence, never narration.** If you cannot point to a
 screenshot / console / observed-state artifact for each passing scenario, the outcome is
 BLOCKED, not SHIP.
- **BLOCKED is a clean surfaced limitation, not a failure to hide.** Set `blocked_reason`.

### Paste-ready handoff

On **NO** (or BLOCKED), the verdict must be paste-ready into a fresh conversation — the next
agent (or the fix author) should not have to rediscover state. Surface, in this order:

1. The **YES/NO call** + the `qa_outcome` (and `blocked_reason` / `na_reason` when set).
2. The **open P0/P1 list** — finding ids + severities + the one-line symptom each.
3. The **R-ID coverage table** (reused from `workflow.md` §2.2, now annotated pass/fail per
 scenario) — the traceability backbone: spec-AC ↔ scenario ↔ finding ↔ R-ID.
4. A **one-paragraph next-step prompt** — what remains unrun, what to re-test after the fix.

QA files, surfaces, and hands off — it **does not fix product code** ("test, document, file,
hand off; don't fix unless asked"). A finding worth fixing is promoted to a flow spec/task
(see [bug-filing.md](bug-filing.md) § Promote), closing the loop back to the originating R-ID.
