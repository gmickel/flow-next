---
satisfies: [R1, R2, R2a, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13]
---
# fn-152-make-pr-opt-in-stack-linking-via-github.1 Implement Dependent-spec chains: branch from the parent, target its PR, link GitHub stacks

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Dependent specs now chain on their parent instead of waiting for its merge. flowctl gained one read-only predicate, `spec chain <id>`, the single owner of chain eligibility (parent open, all tasks done, branch on origin, linear only, one `git ls-remote` at most), and the spec-level admission gate in `ready --spec` / `next` / `ready --all` treats that chain parent as satisfied. Every skill consumer calls the predicate: flow --auto ready and backlog selection (park with the command's reason, no strike; verdict and decision-log reason prefixed `chained on <parent>; `), the attended ladder, work's Phase 2 (branch from the parent's fetched remote tip, spec base = that merge-base, `--branch=current` ancestry check, spec files carried across when the parent tip lacks them), and make-pr (chain rung detected from history via merge-base against the parent's branch tip or merged-PR head, base = parent branch when its PR is open, merged parent rewritten onto the refreshed chain base from the detected boundary on a create run only with a leased push, closed parent / unreachable history exit 2, stack link through the stacks REST API with integer `-F` payloads and a one-line degrade on 404/409/422/transport, `--update` re-inserts the Stack line, chained layers with nothing open born ready). Docs: flowctl.md (`spec chain`, `pilot-log append --reason`), orchestration and teams pages, glossary terms chain/stack/layer/frontier, changelog, and the 2026-08-27 memory entry superseded by the chain rules. Tests: flowctl chain states and admission gates against a bare origin; fence fixtures for every consumer under `set -e` with a stubbed gh.

baseline: green via receipt (unittest green receipt fac401b7 honored at task start); ruff green pre-edit.
GATE_SKIPPED:unittest:green-receipt 0989bb4b - baseline reused from prior post-gate pass (the full suite ran on this exact tree: 220 files, 4991 tests, 0 failures; receipt minted at the fix commit).

Deviation from the conductor's context note: one flowctl change beyond R2/R2a - `pilot-log append --reason` (optional, stored only when given) - because R9 and the spec's Selection section require the backlog decision-log row itself to carry the `chained on <parent>; ` prefix and the row had no reason field. No config key, schema, or `flowctl config` output changed.

Follow-ups noted, not built: make-pr's argument parser still rejects `--update` (pre-existing; the workflow documents `UPDATE_MODE`); the interactive `--ready` override on non-chained PRs with open items is unchanged by spec.

stage: impl-review - ran [codex fan-out over 2591ad0b (round refunded: finalize refused after an early fix commit) -> fan-out over c556ec82 NEEDS_WORK (5 findings) -> fixes 0989bb4b -> single-dispatch re-review SHIP]
## Evidence
- Commits: 2591ad0b20e12b50975acbc0b385282144dde051, c556ec82dcb38227f47313f1ed0da4503258aa99, 0989bb4beb679e5d20ca1dade468b98b4e3002a1
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p test_spec_chain.py (13 tests), python3 -m unittest discover -s plugins/flow-next/tests -p test_chain_consumer_fixtures.py (30 tests), python3 -m unittest discover -s plugins/flow-next/tests -p test_land_chain_fixtures.py (38 tests), uvx ruff@0.16.0 check ., python3 scripts/run_tests_parallel.py (220 files, 4991 tests, 0 failures, run on the tree committed as 0989bb4b), GATE_SKIPPED:unittest:green-receipt 0989bb4b - baseline reused from prior post-gate pass
- PRs: