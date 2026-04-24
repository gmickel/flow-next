# fn-31-pr-feedback-resolver.6 Smoke test scripts + Ralph-isolation verification

## Description

Add a smoke test for the resolver skill + verify Ralph smoke tests remain unchanged (zero new scripts referenced).

**Size:** S-M

**Files:**
- `plugins/flow-next/scripts/resolve-pr_smoke_test.sh` (new)
- Update (no changes expected) `plugins/flow-next/scripts/ralph_smoke_test.sh` — verify it still passes

<!-- Updated by plan-sync: fn-31.3 kept triage / cluster-gate / file-overlap logic as narrative inside workflow.md (no standalone triage.sh / cluster-gate.sh scripts). Smoke coverage for (2)-(4) must be shape-asserted against workflow.md + cluster-analysis.md rather than invoked as pure functions. -->

## resolve-pr_smoke_test.sh

Purpose: validate the scripts + skill wiring with a minimal fixture. Does NOT require a real PR (uses stubbed GraphQL responses via gh's dry-run capabilities or a local JSON fixture).

Scope:

1. **Script sanity**
   - Scripts exist + executable (`get-pr-comments`, `get-thread-for-comment`, `reply-to-pr-thread`, `resolve-pr-thread`)
   - `get-pr-comments --help` (or `bash get-pr-comments` with no arg) fails cleanly with usage message
   - Scripts use `set -euo pipefail`
   - `SKILL.md`, `workflow.md`, `cluster-analysis.md` present with expected frontmatter / phase headers

2. **Triage logic** (documentation-shape test — no standalone triage script exists; triage lives in `workflow.md` Phase 2)
   - Seed a JSON fixture with:
     - 2 new review_threads
     - 1 review_thread with pending-decision reply
     - 2 pr_comments (1 actionable, 1 bot-wrapper)
     - 1 review_body (approval text only)
   - Assert `workflow.md` Phase 2 covers: new/pending split for review_threads, actionability filter + already-replied filter for pr_comments + review_bodies, "Triage: N new, M pending, K dropped" count format.
   - (Optional) If a reusable helper is added later, extend this to also run the fixture through it.

3. **Cluster gate** (documentation-shape test — cluster gate lives in `cluster-analysis.md` + `workflow.md` Phase 3, not a standalone script)
   - Assert `cluster-analysis.md` documents both gate conditions: `cross_invocation.signal == true` AND spatial-overlap precheck.
   - Assert the 11-item category enum is present verbatim.
   - Assert the 4-row cluster-formation table covers match-combinations.

4. **Parallel file-overlap avoidance** (documentation-shape test — logic lives in `workflow.md` Phase 5 narrative)
   - Assert `workflow.md` Phase 5 describes: build file sets per unit, serialize overlapping units, batch size 4 per wave.

5. **Dry-run path** (wiring test)
   - Assert `workflow.md` Phase 4 has a `--dry-run` early-exit that prints the plan before any mutation (Phases 5-8 guarded).

Tests (2)-(4) are shape assertions against the authored markdown (grep / section extraction), not executable logic. If a future refactor extracts triage / cluster-gate / file-overlap logic into scripts, promote these to behavioral tests.

Test runs in a disposable worktree (like `ralph_smoke_test.sh` pattern). Uses `mktemp -d` + cleanup.

Output: pass/fail per test section; overall exit 0 on all pass.

Keep the test ~150-200 LOC. No PR side effects.

## Ralph isolation verification

Run existing Ralph smoke:

```bash
plugins/flow-next/scripts/ralph_smoke_test.sh
```

Verify:
- Completes successfully (same as before fn-31 lands)
- No new scripts invoked (grep the ralph loop for `resolve-pr` — should be zero matches)
- No regression in autonomous behavior

Document in the task PR: "Ralph smoke: N/N passing, resolve-pr not referenced in ralph scripts."

## Acceptance

- **AC1:** `plugins/flow-next/scripts/resolve-pr_smoke_test.sh` exists, executable, runs to completion.
- **AC2:** Smoke covers: script sanity (executable + usage + `set -euo pipefail`), documentation-shape asserts for triage / cluster gate / file-overlap (workflow.md + cluster-analysis.md), dry-run wiring.
- **AC3:** No live PR operations during smoke — all fixtures stubbed or dry-run.
- **AC4:** Existing Ralph smoke test (`ralph_smoke_test.sh`) passes unchanged.
- **AC5:** No ralph script references `resolve-pr` / `flow-next-resolve-pr` / `pr-comment-resolver` (grep-verified).
- **AC6:** Smoke test finishes in under 60 seconds on a modern laptop.

## Dependencies

- fn-31-pr-feedback-resolver.1 (scripts to test)
- fn-31-pr-feedback-resolver.3 (skill to test)
- fn-31-pr-feedback-resolver.4 (cluster-analysis.md to test)
- fn-31-pr-feedback-resolver.5 (flags to test)

## Done summary
Added `plugins/flow-next/scripts/resolve-pr_smoke_test.sh` covering script sanity (executable + strict bash + usage-fails), skill artifacts, workflow.md phase headers, and documentation-shape assertions for triage (Phase 2) / cluster gate (cluster-analysis.md + Phase 3) / file-overlap (Phase 5) / dry-run early-exit (Phase 4). Verified Ralph isolation: zero resolver references in `skills/flow-next-ralph-init/templates/` and `scripts/ralph_smoke_test.sh`; `ralph_smoke_test.sh` still passes 15/15 unchanged. Total runtime ~0.15s, well under the 60s AC6 budget.
## Evidence
- Commits: 2c30631818c0973f3bcb37658e0c0694189c9b3a
- Tests: plugins/flow-next/scripts/resolve-pr_smoke_test.sh (58/58 PASS, ~0.15s), plugins/flow-next/scripts/ralph_smoke_test.sh (15/15 PASS — unchanged, no resolver references)
- PRs: