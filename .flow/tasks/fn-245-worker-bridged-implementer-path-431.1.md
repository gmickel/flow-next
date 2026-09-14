---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-245-worker-bridged-implementer-path-431.1 Implement Worker bridged implementer path (#431 follow-up)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
The worker now owns the CLI bridge when the implementer tier resolves to a model this harness reaches only by shelling out: `plugins/flow-next/agents/worker.md` gains a "Bridged implementer" section (keep Phase 0/1 and the persisted base, skip Phase 1.5 and scout fan-out, compose the pointer prompt plus the usage guide's long-task brief verbatim with the worker's own `TIMEBOX` never copied, run the bridge in one foreground call from the asserted repo root at the commit-permitting sandbox level, commit any dirty remainder, review `<base>..HEAD`, then Phase 3 onward as today). Step 3c in `skills/flow-next-work/phases.md` states the worker bridges and the conductor never does, with `TIMEBOX` as the worker's cap; the `SECTION3C` heredoc in `scripts/sync-codex.sh` carries the implementer-tier paragraph (dropped from the mirror since #352) and the bridge paragraph with two grep guards; `references/no-plan-route.md` narrows the minted-task license on this path to parallel bridge calls on disjoint surfaces in isolated workspaces and branches, research and scouting left to the child; `CHANGELOG.md` Unreleased entry references #431 and #436 and credits the report. Codex mirror regenerated, idempotent on the second run (R6). Prose only, no flowctl code or hook (R1-R7 satisfied).

baseline: green (python3 scripts/run_tests_parallel.py suite_rc=0; uvx ruff@0.16.0 check . passed; no honorable receipt at base, full run executed)

stage: impl-review - ran (codex, 3-draw fan-out round 1 NEEDS_WORK -> single-dispatch round 2 SHIP; findings fixed: concurrent checkpointing children need isolated workspaces and branches, dirty tree committed before range inspection)

stage: plan-sync - skipped(config: planSync.enabled != true)

Follow-up noted, not built: the mirror's `worker.toml` carries the canonical repo path `plugins/flow-next/docs/reach/` as a code span (agent bodies rewrite only `](../docs/` links); harmless in prose, but a Codex-relative pointer would read better.
## Evidence
- Commits: 85204f010f75f3223dae5b1c3db3d7a6621d1622, c6a4872f23bb09f2f9c8ebd2ffa839103921ad2d
- Tests: python3 scripts/run_tests_parallel.py (baseline: green, suite_rc=0, 4991 tests; verify: green, suite_rc=0, 4991 tests), uvx ruff@0.16.0 check . (baseline and verify: All checks passed), ./scripts/sync-codex.sh x2 (exit 0 both runs, empty diff after the second run, before each commit), cd plugins/flow-next/tests && python3 -m unittest test_parallel_work_prose test_worker_anchor_prose test_skill_prose_diet test_foreground_rule_fences test_anchor_bundle test_prompt_text_pinned (OK)
- PRs: