---
satisfies: [R7]
---
# fn-205-issue-sweep-skipped-review-status-land.3 Close pilot, Ralph and the doctrine table on the shared satisfying-member set

## Description
The prose-side half of R7: the gates that read `completion_review_status` directly, outside flowctl. Pilot's stage routing is the one that matters most — left alone it re-routes a policy-excused spec to `work` on every tick, which re-skips and ends the tick, a cross-tick livelock that only exits through the no-advance strike path. Parallel with the work-skill task (disjoint files).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-pilot/workflow.md`, `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh`, `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-common.md`, `plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md`
**Touches:** [plugins/flow-next/skills/flow-next-pilot/workflow.md, plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh, plugins/flow-next/skills/flow-next-spec-completion-review/workflow-common.md, plugins/flow-next/skills/flow-next-tracker-sync/references/status-sync.md]

### Approach
- Pilot route table row at `workflow.md:353` (`all tasks done and completion_review_status != "ship"` -> `work`) becomes a not-in-satisfying-set test. The advancement/logging pair at `:489-502` compares before/after against `ship` too — it must count `not_required` as advanced, or the tick logs a false no-advance and burns a strike.
- Ralph completion gate: `templates/ralph.sh:899` and `:1227-1232` gate on `== "ship" && completion_receipt_ok`. A policy-excused spec has no completion receipt by construction, so the excused member must terminate the gate without demanding a receipt. `:1267-1268` handles `needs_work` and stays.
- `flow-next-spec-completion-review/workflow-common.md:151` states the four downstream consequences of a missing write. That paragraph is now wrong about the skip path — rewrite it to describe the excused member, do not bolt on an exception.
- `flow-next-tracker-sync/references/status-sync.md` is the doctrine `policy.py` claims to port faithfully: update the vocabulary row at `:35` and rows 2/3 at `:105-121` (plus the fixtures at `:675-689`) so the doc and the code agree. A divergence here is a silent contract break with nothing testing it.
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
- [ ] `templates/prompt_completion.md` untouched and its hash pin still green: `cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q`
- [ ] Every gate names the shared satisfying set rather than its own `!= ship` comparison (R7)

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
