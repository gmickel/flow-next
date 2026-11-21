---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-345-efficiency-audit-2026-11-wave-1.1 Implement Efficiency audit 2026-11 wave 1: mechanical fixes and zero-loss prose pruning

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Implemented Wave 1 zero-risk efficiency fixes and zero-loss prose pruning across `plugins/flow-next/` (R1-R6):

- R1: Cut redundant reads, probes, and payload projections in `flow-next`, `flow-next-flow`, `flow-next-capture`, `flow-next-refine`, `flow-next-work`, and `flow-next-spec-completion-review`.
- R2: Added `flowctl pilot snapshot --forge-only --json`, skipped full thread fetch on targeted `resolve-pr` runs (with open-thread filtering and strict pagination error propagation), dropped redundant `gh repo view` / `gh pr view` / `sleep` calls in `make-pr` and `resolve-pr` helpers, and kept reply/resolve as separate GraphQL calls after review flagged GraphQL partial-success risk.
- R3: Fixed `build_rereview_preamble` completion-review ratchet branching, removed duplicate terminal-role heading, shared one immutable diff file per fan-out round across all diff-by-path backends (`claude`, `copilot`, `cursor`, `command`), and tightened effort defaults.
- R4: Extended `flowctl` bootstrap `--help` fast path to Python 3.11-3.13 (28.2 ms median on Python 3.12), batched `flowctl memory audit-scan` git work, and skipped unused locale lookup on `argparse` fast paths.
- R5: Folded `features_status` into `setup-status` and `prime classify`, folded `glossary_terms` into `prime classify`, batched `observability-scout` and `security-scout` passes, validated and cached glossary probe JSON in `flow-next-audit`, and updated `flow-next-plan` startup.
- R6: Collapsed 10 backend-per-file review reference copies into `workflow-cli.md`, folded `autonomous-defaults.md` into `flow-next-flow`, pruned zero-loss same-path prose across skills and references (`-37,641 B` / `-1.78%` canonical across 11 removed files, `-33,924 B` / `-1.14%` Codex mirror), and updated conduct checklists in `agent_docs/conduct/`.

Verification:
- `python3 scripts/run_tests_parallel.py`: 245 files, 4,603 ran, 0 failures, 0 errors, 6 skipped
- `uvx ruff@0.16.0 check .`: passed
- `./scripts/sync-codex.sh --check`: passed
- stage: impl-review - ran (model: gpt-6.2-sol, 3 rounds -> SHIP)
- stage: completion-review - skipped(policy: single-task, per-task SHIP covers spec surface)

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 562a78fc1115449f82ad886343eaeb307f898613, 667b1c5794c61c914372726d90d8d0d14f4051dd, 7b01fd011e534b83d817093bd0a15acee318681c, 01940f53ede2e8fd9d52784e79a4eecea2efddb3, 6dbfda92cd864bd59a8ca97844f6cea5cd266abb, 6de9567d5a695d07d38a3c4fb7a7f61233c9020b, 6c138ee6e1f91823141e995d50e829152dc782c5
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check
- PRs: