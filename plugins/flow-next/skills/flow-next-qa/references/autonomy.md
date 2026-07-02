# Autonomy — Ralph-aware-not-blocked + opt-in tracker post + graceful degradation

This reference carries the full Phase A contract for `/flow-next:qa` (R9 +
R11 + R13): detect-once Ralph routing, the opt-in `tracker.perEvent.qa` verdict
post, and the graceful-degradation matrix when no live deploy / driver is present.
`workflow.md` Phase A is the entry point; this is the detail it folds.

> **The skill is NOT Ralph-blocked.** QA runs in interactive AND autonomous loops.
> There is **no** top-of-skill `FLOW_RALPH`/`REVIEW_RECEIPT_PATH` exit-2 guard — the
> make-pr §0.0 precedent ([flow-next-make-pr/SKILL.md](../../flow-next-make-pr/SKILL.md)
> "Forbidden"). Detect Ralph once, then route deterministically; never re-probe per phase.

## 1. Detect-once routing (R11)

Detect at the top of the run and route downstream — never re-detect:

```bash
RALPH=0
if [ -n "${REVIEW_RECEIPT_PATH:-}" ] || [ "${FLOW_RALPH:-}" = "1" ]; then
  RALPH=1
fi
```

`AskUserQuestion` is **info-only** — it resolves *undocumented facts* (target URL,
test accounts), NEVER a confirm gate ("shall I QA? / ship?"). Interactive resolves
the same facts via the prompt; Ralph cannot ask, so the SAME undocumented fact routes
to a BLOCKED verdict instead. Both are info prompts, not a gate — there is no
interactive-only "confirm before verdict" step.

| Fact | Interactive (RALPH=0) | Autonomous (RALPH=1) |
|------|-----------------------|----------------------|
| Spec id undetermined (Phase 1.1) | `AskUserQuestion` (info) | hard error, non-zero exit + stderr (no user) |
| Target URL undocumented (Phase 3.1) | `AskUserQuestion` (info) | **BLOCKED** verdict (`blocked_reason`), clean exit |
| Test accounts undocumented (Phase 3.2) | `AskUserQuestion` (info) | **BLOCKED** verdict (`blocked_reason`), clean exit |
| URL + accounts configured | drive → verdict | drive → verdict → receipt (zero prompts) |

The **autonomous happy path**: target URL + test accounts come from the spec / config
/ env → derive → drive → file → emit the `qa_verdict` receipt to the caller-supplied
`--receipt` / `REVIEW_RECEIPT_PATH` (`workflow.md` §6.3). The verdict-emission path is
**identical** to interactive; only the *undocumented-input* branch differs (prompt vs
BLOCKED).

### Why no exit guard

A spec-id-undetermined case under Ralph is a genuine "no user to ask" error (exit
non-zero) — but an undocumented URL/accounts is **not** an error: it is an expected,
surfaced limitation that maps to a BLOCKED verdict (§3). The skill always reaches the
verdict; it never aborts at the top because it detected Ralph. Mirrors make-pr, which
forces `--draft` under Ralph but still creates the PR.

## 2. The four-outcome verdict is the autonomy contract

Ralph consumes the `qa_verdict` receipt's `verdict` field (the Ralph-guard enum
projection — `workflow.md` §6.2). Under Ralph the receipt is the *only* output that
matters; there is no human to read the surfaced summary. So Phase A's whole job is to
guarantee a **valid receipt is always written** — autonomous-pass (SHIP), autonomous-NO
(NEEDS_WORK), no-driveable-UI (NA→SHIP), or can't-verify (BLOCKED→NEEDS_WORK). It never
exits without a receipt under Ralph except the genuine spec-id error.

## 3. Graceful degradation (R13)

No live deploy reachable, OR no driver available (including fn-51 degraded to its
**terminal manual rung**), → surface a **BLOCKED** verdict and add **nothing** to the
base flow. Inherit fn-51's degradation table — do **not** re-derive it. See
[flow-next-drive/SKILL.md](../../flow-next-drive/SKILL.md) "Driver detection & graceful
degradation (all surfaces)":

- **Probe, don't assume.** Detect each non-default rung before planning around it.
  agent-browser is the only assumed-present driver; everything above it is probe-and-degrade.
- **Pick the highest rung that passes; fail soft to the next.** The terminal rung is
  always manual / documented-limitation. For QA that terminal rung = there is nothing
  the skill can drive autonomously → BLOCKED (not a fabricated PASS, not a hard error).
- **BLOCKED ≠ FAIL.** "No ship *claim* on a QA basis," never "the app is broken."

The BLOCKED routing (no live target) is `workflow.md` §4.2; the verdict BLOCKED is
`workflow.md` §6.1 / §6.3 with `blocked_reason` set. **SHIP is forbidden without captured live-app evidence (R1)** —
absent evidence, the outcome is BLOCKED, never SHIP.

## 4. Opt-in tracker verdict post (`tracker.perEvent.qa`, R9)

A **new, additive** `perEvent` leaf (`get_default_tracker_config()`, default `off`).
When opted in AND the bridge is active, post the Phase 6 verdict as a structured
tracker **comment** — gated identically to every fn-52 lifecycle touchpoint
([flow-next-work/SKILL.md](../../flow-next-work/SKILL.md) "Shared gating predicate").

```bash
QA_LEAF="$($FLOWCTL config get tracker.perEvent.qa --json | jq -r '.value')"
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$QA_LEAF" != "off" ] && [ "$QA_LEAF" != "null" ]; then
  # invoke flow-next-tracker-sync (comment op) — best-effort, never blocks the verdict
  :
fi
```

### Why `comment` is the only verb

The leaf accepts **`off` | `comment`** (default `off`). A QA verdict is a *report* —
the only meaningful tracker operation is posting it as a comment. `push` / `pull` /
`reconcile` operate on the issue **body/status** and are nonsensical for a verdict, so
the skill treats **any non-`off` value as `comment`** (it never dispatches a
body/status op from a misconfigured QA leaf). The activation predicate
(`tracker_sync_active`) and `TRACKER_PER_EVENT_LEAVES` are unchanged — `comment` was
already a recognised leaf verb (fn-52); this task only adds the `qa` *key* defaulting
`off`.

### Best-effort + no-op safety

- **Active-AND-opted-in only.** Bridge inactive → no-op. Leaf `off`/`null` → no-op.
  No linked tracker id on the spec → the tracker-sync skill no-ops cleanly. The
  no-tracker path is the documented default and is behaviorally unchanged.
- **Never blocks the verdict.** A tracker failure (no transport, 404 issue, rate
  limit) is swallowed by the tracker-sync skill's own `sync receipt`; the QA verdict
  is already written (§6.3) before this step and is never rolled back on a post failure.
- **Transport lives in flow-next-tracker-sync.** Phase A only gates + delegates — it
  never opens a transport, renders a comment body, or dedups comments itself.

### Receipt-prefix note (v1)

A `qa-*.json` receipt parses to `parse_receipt_path`'s fallback but still validates via
the verdict enum. `parse_receipt_path` is **not** extended in v1 — QA is **not** a hard
Ralph receipt-gate (the planning decision); no `ralph-guard.py` change.
