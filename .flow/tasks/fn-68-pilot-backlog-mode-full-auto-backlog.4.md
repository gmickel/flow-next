---
satisfies: [R1, R4, R6, R7, R9, R10]
---

## Description
Wire backlog mode into the pilot skill (thin hooks → .3's reference) + the `ask` stage + **enforced** invariants:
- **Gate + flags (R1):** `pilot.autonomy` gate (strict `== "backlog"`) + `--backlog`/`--auto` override; the force-gate reads the sibling **`pilot.gateClasses`**. Gate off → pilot unchanged.
- **Stage set + classify/dispatch:** add `triage`/`ask` stages **in front of** CLASSIFY; workable items flow into `plan → … → make-pr` unchanged. Phase 1 runs the tracker-sync pull (`reconcile`) **before** `ready --all` (finding #7); selection skips `status=open` parked items (finding #5). The ask stage dispatches tracker-sync's **`question`** op (.2), enumeration uses the **`list-open`** op.
- **ask stage (R4):** **when a flow spec exists**, write `## Open Questions` (always) with the `<!-- flow-next:question id=… status=open -->` anchor (.2) AND post the tracker comment (same `id`); **for a tracker-only item (no spec)** the question is the **tracker comment alone** ("needs a flow spec — run capture/interview"), **never a spec stub**. Ship a **context-package** (what's blocked, why, what each answer would do, spec/issue id + tick). Never interactive.
- **Verdict grammar (R10):** ADD `ASKED <id> (<n>)` — a **durable park** (sets the `status=open` anchor → next tick skips it). **`TRIAGED <id> <class>` is diagnostic/dry-run ONLY** (round-2 #6): a **live** triage always resolves to a state-changing terminal (`ADVANCED`/`ASKED`/`BLOCKED`/`NEEDS_HUMAN`) so an item never re-selects forever. Keep `NO_WORK` + `DEFERRED_TO_LAND` **VERBATIM**. No `PROMOTED`.
- **Idempotent surfacing (R7):** parked items skipped in selection; an answered question → next tick re-triages + proceeds.
- **Decision-log writes (R9):** each tick calls **`flowctl pilot-log append --id … --action <triaged|advanced|asked|blocked|needs-human> --stage <…> [--cost-tokens …]`** (.1's frozen CLI) — and a live `TRIAGED` always co-occurs with a durable park/advance/block, never a bare no-op.
- **Safety invariants as ENFORCING snippets (R6 + memory `skill-workflow-snippets-must-enforce`):** never-merge, never-author-specs (thin/tracker-only → "needs capture/interview", park; may only fill an obvious blank in an *existing* spec), single-tick (no within-tick multi-item loop), dep-cycle → surface. Bash guards, not prose.

**Size:** M · deps .3 (reference) + .2 (anchor + ops)
**Files:** `plugins/flow-next/skills/flow-next-pilot/SKILL.md`, `plugins/flow-next/skills/flow-next-pilot/workflow.md`, `plugins/flow-next/commands/flow-next/pilot.md` (the `--backlog`/`--auto` arg-hint, finding #10)

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md:59-94` — arg parser + `:102-110` — verdict grammar (ASKED durable; TRIAGED diagnostic) + `:108` stage set + `:122` Forbidden block
- `plugins/flow-next/skills/flow-next-pilot/workflow.md:56-91` — SELECT (pull-before-scan + parked-skip) · `:93-195` — CLASSIFY · `:226-246` — DISPATCH (ask → tracker-sync `question` op)
- `plugins/flow-next/commands/flow-next/pilot.md` — public arg-hint + description

## Key context
Skill prose MUST match the real flowctl + tracker-sync op surface — verify every field/verb/op against live `flowctl --json` (memory `skill-prose-must-match-real-flowctl`: fn-59 = 2 NEEDS_WORK rounds). The R2 ask-block must never sit in a hard-error branch under autonomy (memory `r2-ask-block-must-never-anchor`).

## Acceptance
- [ ] `pilot.autonomy` gate (strict `== "backlog"`) + `--backlog`/`--auto` + `pilot.gateClasses`; `commands/flow-next/pilot.md` arg-hint updated; gate off → byte-for-byte unchanged.
- [ ] `triage`/`ask` in front of CLASSIFY; Phase 1 pulls (reconcile) before `ready --all`, enumerates via `list-open`, skips `status=open` parked items; verdict adds **durable `ASKED`**, `TRIAGED` is **diagnostic/dry-run only** (live triage always state-changing), keeps NO_WORK + DEFERRED_TO_LAND verbatim, no PROMOTED.
- [ ] ask: spec-present → `## Open Questions` (anchor) + tracker `question` comment; **tracker-only → tracker comment alone, never a spec stub**; context-package included; idempotent (parked-skip); each tick appends a `flowctl pilot-log` row.
- [ ] never-merge / never-author / single-tick / dep-cycle-surface are **enforcing bash snippets**.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
