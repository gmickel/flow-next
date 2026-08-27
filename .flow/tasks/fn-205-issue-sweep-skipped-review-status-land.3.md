---
satisfies: [R7]
---
# fn-205-issue-sweep-skipped-review-status-land.3 Close pilot, Ralph and the doctrine table on the shared satisfying-member set

## Description
The prose-side half of R7: the gates that read `completion_review_status` directly, outside flowctl. Pilot's stage routing is the one that matters most — left alone it re-routes a policy-excused spec to `work` on every tick, which re-skips and ends the tick, a cross-tick livelock that only exits through the no-advance strike path. Parallel with the work-skill task (disjoint files).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-pilot/workflow.md`, `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh`, `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-common.md`, `plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md`, `plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md`, `plugins/flow-next/tests/test_ralph_guard.py` (or focused sibling)
**Touches:** [plugins/flow-next/skills/flow-next-pilot/workflow.md, plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh, plugins/flow-next/skills/flow-next-spec-completion-review/workflow-common.md, plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md, plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md, plugins/flow-next/tests/test_ralph_guard.py]

### Approach
- Pilot route table row at `workflow.md:353` (`all tasks done and completion_review_status != "ship"` -> `work`) becomes a not-in-satisfying-set test. The advancement/logging pair at `:489-502` compares before/after against `ship` too — it must count `not_required` as advanced, or the tick logs a false no-advance and burns a strike.
- Ralph completion gate, corrected shape (verified 2026-08-27): `templates/ralph.sh:899-900` is a bare `!= "ship"` continue inside `maybe_close_specs` with a SEPARATE `verify_receipt` check at `:905`; the compound `== "ship" && completion_receipt_ok` form is only at `:1228` (with `:1232` handling `needs_work`). Both sites move to the satisfying-set test, and a policy-excused spec has no completion receipt by construction, so the excused member must pass without demanding one — at `:905` as well as `:1228`. `:1267-1270`'s status→verdict case keeps `ship`/`needs_work` as-is (do not map `not_required` to a verdict — no review ran). `:1006` (`--require-completion-review` activation) needs no edit; flowctl's predicate change covers it. The progress log (`:700`,`:720`,`:1325`) will start showing `not_required` — cosmetic, no edit.
- `flow-next-spec-completion-review/workflow-common.md:151` states the four downstream consequences of a missing write. That paragraph is now wrong about the skip path — rewrite it to describe the excused member, do not bolt on an exception. While rewriting, fix its pre-existing factual error: it cites `flowctl ready --require-completion-review`, but the flag exists only on `next` (`flowctl.py:50443`).
- New reader (verified 2026-08-27): `flow-next-spec-completion-review/SKILL.md:132` — the Step 0.5 idempotent-terminal checkpoint reads the stored status to decide whether to re-run/re-write. Classify `not_required` explicitly: it is not `ship` (an explicit manual invocation may still run a real review and overwrite to `ship`/`needs_work` — the upgrade direction is legal; the skip's own write remains gated on `unknown`), but the checkpoint must not treat it as `unknown` either. State the classification in the prose, one clause.
- make-pr's reads (`workflow.md:920,925,983`; `create-and-finalize.md:101,103,397`) are `== needs_work` predicates — member-safe for `not_required` by construction. Verify, do not edit.
- `flow-next-tracker-sync/references/status-sync.md` is the doctrine `policy.py` claims to port faithfully: update the vocabulary row at `:35` and rows 2/3 at `:105-121` (plus the fixtures at `:673-689`) so the doc and the code agree. A divergence here is a silent contract break with nothing testing it. Two pre-existing defects to fix in the same pass: the `:35` vocabulary row already omits `needs_human` (list all five members), and `:677` cites `flow-next-pilot/workflow.md:117-122`, which is stale — the route row now lives at `:353`.
- Out of scope, deliberately: `flow-next-ralph-init/templates/prompt_completion.md:38-39` writes `ship` when the completion backend is `none`. Same anti-pattern, different trigger, and the file is SHA-pinned — the spec Boundaries park it. Do not edit it; if you believe it must change, report it rather than widening the task.
- Do NOT run `./scripts/sync-codex.sh` (finalization owns the single regen).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-pilot/workflow.md:345-358` — the first-match-wins stage table and the strike/no-advance semantics beneath it
- `plugins/flow-next/skills/flow-next-pilot/workflow.md:489-502` — advancement detection and the before/after status log
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:890-905` and `:1220-1240` — the completion gate and its receipt pairing
- `plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md:100-125` — the doctrine rows the projection ports

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-common.md:140-160` — the consequences paragraph to rewrite

### Key context
- Pilot line `:358` already documents that an unconfigured review backend skips the gate entirely; the excused member is the configured-backend analogue of that, so the wording can lean on the existing sentence instead of introducing a new concept.

### Acceptance
- [ ] Pilot never routes an all-tasks-done spec carrying the excused member back to `work` (R7)
- [ ] Pilot's advancement logging treats the excused member as satisfied, so no false no-advance strike is recorded
- [ ] The Ralph completion gate terminates on the excused member without requiring a completion receipt; `needs_work` handling unchanged
- [ ] `workflow-common.md`'s consequences paragraph describes the excused member accurately (rewritten, not appended to)
- [ ] `status-sync.md`'s vocabulary row, projection rows and fixtures match `policy.py`'s behavior exactly
- [ ] An executable test pins the Ralph completion gate's classification for every member (`ship`, `not_required`, `needs_work`, `needs_human`, `unknown`, absent, unrecognized) — extend `test_ralph_guard.py`/`test_ralphctl.py` prior art or add a focused sibling; `not_required` terminates without a receipt, `ship` still demands one (R7)
- [ ] Pilot/checkpoint prose gates carry NO sentence-level test pins (repo doctrine, 2026-08-07 ban) — their coverage is the conduct checklist added in the finalization task; state this in the done summary so the gap reads as a decision
- [ ] `templates/prompt_completion.md` untouched and its hash pin still green: `cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q`
- [ ] spec-completion-review's Step 0.5 checkpoint classifies `not_required` explicitly (not `ship`, not `unknown`; manual re-run may upgrade it to a real verdict)
- [ ] status-sync.md's pre-existing defects fixed in passing: `:35` vocabulary lists all five members (incl. `needs_human`), `:677`'s stale pilot anchor repointed to the route table
- [ ] Every gate names the shared satisfying set rather than its own `!= ship` comparison (R7)

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
