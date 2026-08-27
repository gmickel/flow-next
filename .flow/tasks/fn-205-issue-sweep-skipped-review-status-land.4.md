---
satisfies: [R4]
---
# fn-205-issue-sweep-skipped-review-status-land.4 Land tail: commit the tracked sidecar without ever naming ignored receipts

## Description
Fix the post-merge sync-state step so the tracked spec sidecar commit lands regardless of the auto-ignored receipt directory (R4), and — only if it costs no machinery — add the one-sentence "one land host per checkout" note the ledger region already has the context for (issue #368 option 2). Fully disjoint from the other tasks; runs in the first wave.

**Size:** S/M
**Files:** `plugins/flow-next/skills/flow-next-land/workflow.md`, `plugins/flow-next/tests/test_land_config.py`
**Touches:** [plugins/flow-next/skills/flow-next-land/workflow.md, plugins/flow-next/tests/test_land_config.py]

### Approach
- The bug is the inline command at `workflow.md:784`: a single `git add` naming both the tracked sidecar and `.flow/sync-runs`, chained with `&&` to the commit. `.flow/sync-runs/` is in flowctl's auto-ignore block (`flowctl.py:19577`) and that block is reconciled on upgrade, which is why the step broke retroactively in repos that were already set up.
- Fix by avoidance, not recovery: never pass an ignored path to `git add`. Naming only the tracked sidecar removes the whole failure class — an exactly-named ignored path exits 1 while leaving the tracked file staged (verified), and an absent path exits 128. Receipts are runtime artifacts and stay untracked (spec Boundaries); do not reach for `-f`, and do not change the ignore set.
- Make a no-op a success: when the touchpoint did not edit the sidecar there is nothing to commit, and the step must not report a failure. Guard the commit on a staged-diff check rather than letting the commit's exit code stand in for an error. The prior art is make-pr's advisory git chain, which guards each step individually.
- Preserve the tail's existing shape exactly: two file-scoped `.flow` commits (close at `:718`, sync state at `:784`) riding step 4's single push, with the range rollback `git reset --hard "$TAIL_BASE_OID"` and its non-`.flow` path guard at `:802-816`. A two-statement add-then-commit inside step 3 is rollback-safe by construction. `test_land_config.py:976` bans the `HEAD^` form — keep it banned.
- Keep the existing rationale prose (file-scoped so pre-existing `.flow` dirtiness never rides along) and drop only the receipts claim, which was never achievable once the directory became ignored.
- `resume-tail` (`:821-823`) re-runs the whole tail; verify the fixed step is idempotent when the sidecar is already committed.
- #368 sentence: the ledger-resolution region at `:92-98` already explains the store is a git-common-dir scratch file shared across worktrees. One clause there stating that land state is per-checkout, so one land host per checkout, is the zero-machinery option. If it cannot be said in a sentence without new structure, skip it and say so — no committed ledger, no tracker-carried land state.
- Do NOT run `./scripts/sync-codex.sh` (finalization owns the single regen).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-land/workflow.md:769-790` — the touchpoint dispatch and the broken sync-state commit
- `plugins/flow-next/skills/flow-next-land/workflow.md:800-818` — the persist step and the guarded range rollback the fix must preserve
- `plugins/flow-next/tests/test_land_config.py:960-980` — the existing tail assertions (commit subject, rollback shape, `HEAD^` ban)
- `plugins/flow-next/scripts/flowctl.py:19565-19600` — the auto-ignore pattern list, including `sync-runs/`

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-land/workflow.md:92-98` — ledger resolution, the candidate home for the #368 sentence

### Key context
- R4 has zero existing test coverage: `test_land_config.py` pins the commit subject and the rollback but nothing about which paths are staged. New assertions are required, not amended ones.

### Acceptance
- [ ] The sync-state step's pathspec names only tracked spec-sidecar path(s); `.flow/sync-runs` is never passed to `git add` (R4)
- [ ] The sidecar commit lands whether the receipt directory is present-and-ignored or absent, and ignored receipts are never staged (R4)
- [ ] A sidecar the touchpoint did not change is treated as success with nothing committed, not as a failure (R4)
- [ ] No path can leave the sidecar staged-uncommitted (R4)
- [ ] The two file-scoped `.flow` commits, the single push, and the `TAIL_BASE_OID` range rollback with its non-`.flow` guard are unchanged; `HEAD^` still absent
- [ ] `resume-tail` over an already-committed sidecar reports success
- [ ] New assertions in `test_land_config.py` pin the pathspec and the guarded commit; `cd plugins/flow-next/tests && python3 -m unittest test_land_config test_flow_gitignore -q` green
- [ ] The #368 one-sentence note added at the ledger region, or explicitly reported as skipped for costing machinery

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
