---
satisfies: [R1, R1b, R3, R6, R7]
---

## Description

Wire `qa` as an **optional, config-gated, idempotent pilot stage** at all-tasks-done, before make-pr, and **surface its verdict into the draft PR**. Reverses pilot's explicit "QA is never a stage" constraint **only under the gate**; the other five forbidden items stay forbidden. Pilot orchestration + a one-line config-default + a make-pr read — **no new flowctl subcommand/engine**; pilot dispatches the (evidence-aware) QA skill from task .1.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-pilot/{SKILL.md,workflow.md}`, `plugins/flow-next/skills/flow-next-make-pr/workflow.md` (PR-body surfacing), `scripts/flowctl.py` (`pipeline.qa` config default), `docs/flowctl.md` (config row), `tests/` (regression)

## Approach

- **Config default (the one mechanical flowctl touch):** register `"pipeline": {"qa": "off"}` in `get_default_config()` (so `config get pipeline.qa` returns `off`, not `null`), mirroring `artifacts.html.enabled`. No new subcommand. Add a focused config test (like the artifacts-config test) + a `pipeline.qa` row to the `docs/flowctl.md` config table — **document the enum value `off`/`on`, not `true`** (memory `docs-activation-command-for-string-enum`).
- **Gate read:** the canonical 3-clause guard (`config get pipeline.qa --json | jq -r '.value'` != `off` && != `null`), modelled on `flow-next-work/phases.md:211-212`.
- **Forbidden-list reversal (under the gate only):** `flow-next-pilot/SKILL.md:122` — remove `QA` from "never pilot stages" *when `pipeline.qa==on`*; keep capture/interview/resolve-pr/merge/release forbidden. Add `qa` to the stage enums (`SKILL.md:3,10,108`).
- **Placement + idempotence (R1/R1b):** classify table `workflow.md:111-118`; the all-done juncture is `workflow.md:135-141` — insert the `qa` classification **ahead of the "no PR → make-pr" branch (`:139`)**. Gate it on **absence of a *fresh* `qa_verdict` receipt** — fresh iff `receipt.id == <spec-id>` (the receipt's existing spec-id field, `flow-next-qa/workflow.md:423`) AND `receipt.head_sha == $(git rev-parse HEAD)` AND a valid terminal `qa_outcome` (the `head_sha` field is added by task .1). All-done + `pipeline.qa==on` + no fresh receipt ⇒ classify `qa`; a fresh receipt ⇒ fall through to the make-pr probe. (Single-tick pilot would otherwise re-classify `qa` forever.) **Branch-safety:** at *classification* time compute freshness against the spec-branch head (`git rev-parse "$BRANCH_NAME"`) — a resumed/manual tick may be on another branch; after the branch checkout, `HEAD` is correct for the post-dispatch verify.
- **Branch matrix (`:162-173`) — explicit `qa` rows:** branch exists ⇒ `git checkout <branch>` + drive the running app (never default-branch); branch absent at all-done ⇒ `NEEDS_HUMAN` (inconsistent all-done/no-branch), not a silent skip.
- **Dispatch (`:185-191`)** → `/flow-next:qa <spec-id> mode:autonomous`. Pre-dispatch snapshot (`:178-184`) + verify/evidence-echo (`:196-251`): **advancement is verified from observed state, never sub-skill narration** — for `qa`, `advanced=true` iff a fresh `qa_verdict` exists *after* dispatch (`receipt.id == <spec-id>` AND `receipt.head_sha == HEAD` AND valid `qa_outcome`); echo `stage=qa qa_outcome=<…> head_sha=<…> advanced=<true|false>`. A missing/stale receipt ⇒ `advanced=false` (do not advance on narration).
- **Gate routing reads `qa_outcome`, NOT the `verdict` projection** (`flow-next-qa/workflow.md:378-389` projects `BLOCKED→verdict=NEEDS_WORK`): `SHIP`/`NA`/`BLOCKED` → advance; `NEEDS_WORK` → still advance to make-pr (draft) **and surface findings**. Never hard-blocks the loop — human review + land act on it.
- **PR-body surfacing owner (R7 implementation):** `flow-next-make-pr/workflow.md` reads `.flow/review-receipts/qa-<spec-id>.json` (when present) and includes `qa_outcome`, the persisted `open_p0p1` objects, any BLOCKED/NA reason, and the persisted `rid_coverage` summary in the PR body (all fields task .1 adds to the receipt) — so "surface into PR" has a concrete owner. (NEEDS_WORK also feeds bug-memory + tracker comment when active, as today.)
- **Don't-thrash + non-fatal:** bound any work↔qa re-pass at 2–3 cycles (failure-stop) + a turn ceiling (budget-stop); missing app ⇒ BLOCKED→advance, never a failed loop. Shell snippets **guarded** (no bare `git`/side-effects under `set -e`; memory `optional-side-effect-snippets-need`). Any receipt JSON composed via the **existing QA receipt writer (Python `json.dump`)** or `jq -n` — **no heredoc interpolation** (memory `heredoc-built-json-breaks`).
- **Match real flowctl** — field names/enums must match exactly (memory `skill-prose-must-match-real-flowctl`; fn-59 needed 2 rounds).

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-pilot/SKILL.md:3,10,108,122` — stage enums + Forbidden list
- `plugins/flow-next/skills/flow-next-pilot/workflow.md:111-118,135-141,162-173,178-191,196-251` — classify / all-done / branch / dispatch / verify-echo
- `plugins/flow-next/skills/flow-next-qa/workflow.md:362-411` — qa_outcome matrix + BLOCKED→verdict projection + receipt path
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md` — PR-body assembly (where to inject the qa summary)
- `scripts/flowctl.py` `get_default_config()` + the artifacts-config test — the config-default pattern + test
- `plugins/flow-next/skills/flow-next-work/phases.md:211-212` — the 3-clause config gate
**Optional:**
- `plugins/flow-next/skills/flow-next-qa/references/autonomy.md` — BLOCKED/NA degradation

## Acceptance
- [ ] `pipeline.qa` default `off` registered in `get_default_config()` (+ config test); `config get pipeline.qa` returns `off` not `null`; documented with the enum value in `docs/flowctl.md`. Off ⇒ pilot's stage set + behavior byte-for-byte unchanged.
- [ ] Forbidden-list "QA never a stage" reversed **only under the gate**; capture/interview/resolve-pr/merge/release remain forbidden; `qa` added to stage enums + classify/branch/dispatch/verify-echo at the all-done juncture before make-pr.
- [ ] **Idempotent:** `qa` is classified only when no fresh `qa_verdict` receipt exists; a current receipt falls through to make-pr (no infinite re-classify on single-tick pilot).
- [ ] Branch matrix has explicit `qa` rows (checkout existing branch; absent-branch ⇒ NEEDS_HUMAN).
- [ ] Gate routes on `qa_outcome` (NOT `verdict`): SHIP/NA/BLOCKED advance; NEEDS_WORK advances to the draft PR + surfaces findings; never hard-blocks.
- [ ] `flow-next-make-pr` includes the qa summary (outcome + persisted `open_p0p1` + BLOCKED/NA reason + `rid_coverage`) in the PR body when a receipt is present.
- [ ] Freshness/verify use the receipt's existing `id` field + `head_sha == git rev-parse HEAD` (not `spec`, not mere file presence).
- [ ] Pilot verifies `qa` advancement from the post-dispatch receipt (observed state), echoing `qa_outcome`/`head_sha`/`advanced`; never advances on sub-skill narration.
- [ ] Bounded work↔qa (2–3 cycles + turn ceiling); missing app → BLOCKED→advance; shell guarded; receipt JSON via the existing Python writer / `jq -n`, no heredoc interpolation.
- [ ] Regression coverage: `pipeline.qa` default-off; pilot docs include the `qa` stage enum; routing reads `qa_outcome` not `verdict`; receipt-present ⇒ skip-to-make-pr. No new flowctl subcommand; flowctl field names/enums match exactly.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
