---
satisfies: [R3, R4, R5]
---
# fn-180-declared-vs-evidenced-r-id-coverage.3 validate: batched evidence-commit reachability finding

## Description
Spec fn-180 items 2-3 (#302). Three-state finding per evidence.commits[] entry: reachable (silent), present-but-orphaned (finding), non-commit token (ignored). MUST batch: one cat-file --batch-check over all tokens + one membership pass; constant git spawns regardless of commit count. No auto-rewrite anywhere. make-pr must not render an orphaned SHA link unmarked.

**Files:** plugins/flow-next/scripts/flowctl.py (validate) + `.flow/bin/flowctl.py` dual copy; validate tests

## Acceptance
R3, R4, R5 of the spec. Fixture covers all three states incl. foreign-hex survival; spawn count asserted or inspected.

## Done summary
validate evidence reachability per fn-180 R3-R5 (#302). New EvidenceReachability classifier shared across the whole validate invocation (incl. --all): one git cat-file --batch-check over all hex-shaped tokens via stdin + one streamed git rev-list HEAD membership walk abandoned once every candidate oid is seen - exactly 2 spawns regardless of commit/spec count (R4; frozen subprocess inventory updated with rationale). Three states per token: reachable silent, present-but-orphaned warning ("orphaned by a history rewrite; recorded value left as-is"), non-commit tokens ignored by contract (UUIDs/foreign SHAs never probed as refs, only ^[0-9a-f]{7,40}$ reaches git). Every git failure mode degrades to ignored - validate never crashes. Warnings ride the existing shape, valid stays true, exit 0. No auto-rewrite anywhere (R5). Dogfood: our own repo shows ~40 genuine squash-merge orphans in 0.85s.
## Evidence
- Commits: 756971cf
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_evidence_reachability test_validate_all_diagnostics test_tracker_distribution test_bin_launcher_parity test_prompt_text_pinned test_hot_path_sweep -q (56 OK), python3 scripts/run_tests_parallel.py (4401 OK)
- PRs: