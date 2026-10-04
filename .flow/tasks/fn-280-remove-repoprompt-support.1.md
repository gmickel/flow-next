---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9]
---
# fn-280-remove-repoprompt-support.1 Implement Remove RepoPrompt support

## Description
TBD

## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
RepoPrompt is removed. The `rp` backend is gone from the registry, the config schema, setup, skills, commands, the worker agent and the docs. Also removed: flowctl's `rp` command group and CLI plumbing (about 1,075 lines), `/flow-next:export-context`, plan review's export mode, and the three RepoPrompt review workflows. A stale `rp`/`export` value (config, FLOW_REVIEW_BACKEND, a task's review, a spec's default_review, or `--review=`) prints one stderr notice and resolves to no reviewer configured (`ASK`) without falling through. Writes of `rp` are refused with the same text. `review-rounds record --backend` is now required. QA receipt-driven mode is `receipt`; legacy `rp` receipts still read and keep their findings lineage.

Tier: session (jev intelligent 0.52)

Evidence (measured):
- Full suite `python3 scripts/run_tests_parallel.py`: 214 files, 3,930 tests, 0 failures. Ruff, `sync-codex.sh --check`, `check_doc_anchors.py` and the python3.14 help hash all pass.
- CI smokes, each run from a scratch dir: all pass except two live `copilot plan-review/impl-review e2e` cases in smoke_test.sh. Those are INCONCLUSIVE: the Copilot plan's usage limit rejected the calls ("You've reached your additional usage limit"). The other 129 pass, including the new "set-backend rejects removed rp backend". ci_test.sh: 55/0.
- R1 error surface: `test_backend_spec.py::TestRemovedReviewBackendCli` (config/env/task/spec tables plus `config set` rejection, through the real CLI) and `test_tracker_status.py::...::test_removed_backend_reads_as_not_configured`.
- R4: `test_review_findings_receipts.py::...::test_legacy_rp_receipt_on_disk_still_reads`, `test_artifact_writers.py::test_qa_receipt_extends_a_legacy_rp_mode_receipt`, `test_resume_terminal.py` (the legacy rp recovery gate is kept).
- R9: fn-271 same-load A/B on case gno-216, 7.1.2 tag vs 62e7bcc7, two pairs (rounds fn280-r9{A2,B2,A3,B3}-1004). Hidden checks 4/4. Judge 19/18 vs 19/19 and 19/20 vs 18/20 (same mean). First handoff 202/132 s vs 125/172 s (median 167 vs 149). Wall 378/237 s vs 613/309 s; cost $1.34/$0.97 vs $2.64/$1.46. B2's extra wall came from a second person exchange: its codex reviewer found a real case defect (connector verification), and the person's answer asked for more. B3's came from model time (149 vs 72 s) and a longer codex review. On this route the instruction text differs from 7.1.2 by one impl-review bullet that fires only on rp/export, so the gaps are draw variance with no mechanism behind them (inferred). n=2: a larger same-load A/B is the maintainer's call if wanted.

Decisions:
- Following R1's "behaves as no reviewer configured", a stale value at any precedence level resolves to ASK and does not fall through. Setup treats a stale `rp` as unset and re-asks.
- R8: changelog entry under Unreleased. The flow-next.dev, AI x SDLC guide and mickel.tech updates are release-time and not done here.

Follow-ups (not part of this task):
- Pre-existing: `spec/task set-backend` errors print `Invalid spec for <function field at 0x...>` because flowctl.py uses `field` instead of `_field_name`, at two sites.
- Coverage note: the deleted export fixtures were the only tests of the `Severity = X` and `Nitpick`->P3 parser forms; the parser still accepts both.
- agent_docs/docs-conventions.md says a count test pins the skills table; no such test exists (pre-existing).

stage: impl-review - ran [codex fan-out NEEDS_WORK (5 findings, all fixed in 62e7bcc7) -> re-review SHIP]

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: e06ddc0156b172aa717aa1816e827f58c0204e07, 62e7bcc7025c29b80288a68d63c54ab5b6287105
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check, python3 scripts/check_doc_anchors.py, CI functional smokes from scratch dirs (smoke_test.sh: 129 pass, 2 copilot e2e INCONCLUSIVE - copilot usage limit), fn-271 A/B gno-216 x2 pairs vs flow-next-v7.1.2
- PRs: