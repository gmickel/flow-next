---
satisfies: [R5, R6, R7, R9]
---
# fn-145-opus-5-autonomous-seam-retune.3 Route host review mechanics behind selected references

## Description
Finish progressive disclosure for the host review backend. Keep only minimal
recognition/routing and safety invariants in root review skills; make the
selected host workflows self-contained; clarify that completion-review status
is owned by the shared status step exactly once.

**Size:** M

**Files:**
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md`
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md`
- `plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md`
- `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-host.md`
- `plugins/flow-next/tests/test_host_review_backend.py`
- relevant prose/reached-path tests under `plugins/flow-next/tests/`

### Approach

- Root skills retain bare-only `host` grammar, selected-reference routing, and
  one concise fresh/read-only cross-family fail-closed invariant.
- Move platform dispatch, receipt, re-review, and backend-specific mechanics
  behind `workflow-host.md`.
- Remove alternative status-write language from completion host workflow; its
  verdict continues into the shared fix loop/status owner.

### Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-impl-review/SKILL.md:85-115`
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md`
- `plugins/flow-next/skills/flow-next-spec-completion-review/SKILL.md:85-110,185-210`
- `plugins/flow-next/skills/flow-next-spec-completion-review/workflow-host.md:65-90`
- `plugins/flow-next/skills/flow-next-*/workflow-common.md`

**Optional:**
- `.flow/specs/fn-123-cursor-first-class-experience-team.md`
- `.flow/specs/fn-130-reached-path-skill-prompt-optimization.md`
- `plugins/flow-next/tests/test_host_review_backend.py`

### Key context

Missing cross-family pins remain fail-closed. `NEEDS_HUMAN`, transport failure,
and retry outcomes must not write terminal completion status.

## Acceptance
- [ ] Both root review skills contain only minimal host recognition/routing and
  the concise fresh/read-only/fail-closed invariant.
- [ ] Host workflow references contain all selected-backend mechanics needed
  for dispatch, receipt handling, fixes, re-review, and fail-closed behavior.
- [ ] Non-host reached paths keep host-specific mechanics cold.
- [ ] Host completion workflow never writes or offers to write terminal status;
  the shared owner writes it exactly once for terminal outcomes.
- [ ] Host backend and reached-path tests cover cold loading and status
  ownership and pass.


## Done summary
Minimized host-specific mechanics in both review root skills, keeping only bare-host routing and the fresh/read-only/cross-family fail-closed invariant. Made both selected host workflows self-contained for dispatch, receipts, fixes, fresh re-review, and failure handling; completion status now has one shared terminal owner, with focused cold-load and status-ownership coverage.

Focused baseline: 102 tests passed. Focused post-change/post-commit verification: 106 tests passed. Full suite, Ruff, and Codex mirror regeneration intentionally deferred to integration task fn-145-opus-5-autonomous-seam-retune.4.
## Evidence
- Commits: ea5fc9274e38a0f8e9ce2653615338660a324860
- Tests: focused six-module suite (106 passed), python3 -m unittest test_host_review_backend -q (14 passed in fresh review)
- PRs: