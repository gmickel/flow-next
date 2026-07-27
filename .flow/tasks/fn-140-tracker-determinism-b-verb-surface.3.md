---
satisfies: [R6, R7, R8]
---
# fn-140-tracker-determinism-b-verb-surface.3 status verb: fn-66 evidence gate + who-wins ladder

## Description
Implement `tracker status <spec-id> --to <normalized>`, embedding **fn-66's merge-evidence gate** rather than forwarding the caller's request: terminal `Done` only on a GitHub-confirmed MERGED, `In Review` on an open PR, never terminal from completion-review alone.

Port the who-wins ladder **preserving branch order** - collision cases first. Memory `who-wins-ladder-must-check-the-...` records that reordering lets an earlier rule silently win. Enumerate deterministic outcomes for deadlock fallback and unmapped states; genuinely ambiguous cases return `class: conflict` for the skill's recovery surface.

Jira uses the cached target STATUS id, then GETs the issue's legal transitions first - transition ids are valid only from the current status (`jira.md:738`, verified live: To Do/In Progress/Done each surfaced different ids). No legal transition to the target means defer + receipt, never a forced jump. GitHub's undocumented `duplicate` reason is reachable via `--reason`.

## Acceptance
- [ ] Completion-review alone cannot produce terminal Done
- [ ] Collision branches evaluate before single-field rules; a reordering test fails
- [ ] Jira resolves legal transitions per issue; no cached transition id is used
- [ ] No legal transition -> defer + receipt, never an illegal jump
- [ ] Unmapped/deadlock states return `class: conflict`, never a silent default
- [ ] `--reason duplicate` reachable on GitHub; garbage reason 422s
- [ ] GitLab states handled as `opened`/`closed`

## Done summary
tracker status shipped: fn-66 merge-evidence gate + who-wins ladder (grok-4.5 implementation, host + codex hardening over 4 rounds).

status/ package: merge_evidence (gh pr list probe, canonical buckets - open+closed IS ambiguous per status-sync.md), the 8-row flow->normalized table (terminal ONLY from confirmed MERGED, PR rows beat task rows), decide() with the final load-bearing order deadlock -> non-clean-evidence conflict -> equality noop -> tracker-terminal LOCAL fold (spec status + lastSyncedAt + pulled receipt, no tracker mutation) -> merge-gate -> single-field rules -> residual conflict. --to is a request; --reason enumerated (github duplicate reachable, garbage 422s pre-request); cancelled-family surfaced never applied; ambiguity returns class conflict for the skill recovery surface; applied advances lastSyncedAt, noop/defer/conflict never do; defer receipts mandatory (write errors propagate). Providers: github PATCH state/state_reason + single-valued status:* label with partial-mutation accounting (completed_steps + labels-degraded readback), gitlab state_event opened/closed, linear stateId from resolved cache, jira per-issue legal transitions vs cached STATUS ids (no transition cached; no legal path -> defer + receipt).

4 codex rounds: 5 -> 2 -> 1 -> SHIP; ordering bugs each pinned by composition tests (incl. the reviewer catching a host 'improvement' that contradicted the canonical doc - reverted).
## Evidence
- Commits: a85f0a6d, 26c6c622, e4582e06, 44479fbe
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_tracker_status -q, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs: