---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-244-bridged-implementer-may-commit.1 Implement Bridged implementer may commit checkpoints; timebox-free brief for long bridged tasks (#431)

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Relaxed the bridge safety rule so a bridged implementer may commit checkpoints on the branch the host names (never push, rebase or rewrite history, decide scope, issue a verdict, or spawn a bridge; the host keeps push, review, `flowctl done`, task state, and any history rewrite), stated the host's on-return obligation (record base, review `<base>..HEAD`, run the gates on that diff, host-owned squash-or-keep), and added a timebox-free brief template for long bridged tasks with the sandbox-denied fallback. Applied to the usage template and its Codex mirror (regenerated via sync-codex.sh, idempotent), the orchestration guide (bridge route, host-model paragraph, field-pattern table, "What stays fixed"), the running-lean pointer, this repo's CLAUDE.md/AGENTS.md routing blocks, and a CHANGELOG Unreleased entry crediting @DanielKillenberger (#431).

Verified live rather than asserted: codex 0.153.4 `--sandbox workspace-write` keeps `.git/` read-only (`git commit` fails with `index.lock: Read-only file system`, exit 128); `--sandbox danger-full-access` commits. The usage recipe names that flag for a checkpointing child in the asserted repo root, else the one-run-per-scope-unit fallback.

baseline: green (python3 scripts/run_tests_parallel.py suite_rc=0, 4991 ran; uvx ruff@0.16.0 check . clean)
verify: green at HEAD (same commands; receipt .flow/tmp/green-receipts/15792ae4-unittest.json)

R-ID coverage: R1-R6 satisfied in commit 15792ae4. R7 (flow-next.dev work page, model-routing guide, cookbook entry, landing-page card; reply on #431) is deferred to the downstream release walk in ~/work/flow-next.dev per the spec.

Follow-ups (not built): `plugins/flow-next/docs/release-history.md` 4.0.0 line still describes the old rule as history; the release walk may append an entry for this change once the version is known. The spec's "byte-identical mirror" edge case is inexact: the Codex mirror carries the pre-existing `/flow-next:x` -> `$flow-next-x` transform (12 diff lines at both base and HEAD); the edit carried through identically.

stage: impl-review - ran (codex fan-out, 3 draws gpt-6-astra:high, all SHIP, 0 findings; receipt /tmp/impl-review-receipt-6a743e80ce39-fn-244-bridged-implementer-may-commit.1.json)
## Evidence
- Commits: 15792ae478d5a9fa8b8d1d60c10f55a0c0fa08a9
- Tests: python3 scripts/run_tests_parallel.py (baseline: green, suite_rc=0, 4991 ran; verify at HEAD: green, suite_rc=0, 4991 ran, receipt .flow/tmp/green-receipts/15792ae4-unittest.json), uvx ruff@0.16.0 check . (baseline green; verify green), ./scripts/sync-codex.sh x2 (idempotent, rc=0 both), live probe: codex exec 0.153.4 --sandbox workspace-write denies git commit (index.lock: Read-only file system, exit 128); --sandbox danger-full-access commits (exit 0)
- PRs: