---
satisfies: [R4, R6, R8]
---
# fn-215-parallel-draw-review-three-axis-lenses.3 Docs sweep + CHANGELOG: teach the dials, positive formulation

## Description
**Touches:** plugins/flow-next/docs/**, CHANGELOG.md, agent_docs/**, plugins/flow-next/codex/docs/**

Repo docs per the docs-gap map: orchestration.md review-backends section (three-draw default, same resolved backend; the WORKED STEERING-RECIPES subsection lives here + running-lean — the repo-side recipe R6 requires now), running-lean.md cross-model dial (cost bullet = ~three draws; single-reviewer economy phrasing; table row notes prose-steered-not-a-knob), flowctl.md deterministic-review-cap section (merged round = one reservation, both backends), review-findings.md merge subsection (union re-ordinaled 1..N, deferred remainder lineage, no axis field on items), skills.md impl-review row, docs/README.md Notable updates entry, CHANGELOG Unreleased entry (user-outcome-first: expected to dramatically shorten iterative review churn — round-density claim per the studies; names the site cookbook page as pending release-time downstream). Frame inside reviews-being-optional; positive formulation both dials. Re-run docs pin suites (test_ralph_docs_truth, test_review_findings_docs, skills.md-referencing suites) + FULL parallel suite + pinned ruff (docs-tree rule).
## Acceptance
R4 (documented round semantics), R6, R8 satisfied; judge against the parent spec's criteria directly. Full gate green.

## Done summary
Shipped the repo-side docs for the parallel-draw fan-out (R4, R6, R8): orchestration.md review-backends section (three-draw default, worked steering recipes for both dials — single-reviewer economy and cross-family upgrade with the codex-primary constraint and rationale), running-lean.md cross-model dial (cost bullet, prose-steered-not-a-knob), flowctl.md deterministic-review-cap (merged round = one reservation, both backends) + the fan-out CLI block, review-findings.md merge subsection (union re-ordinaled 1..N, deferred remainder lineage, no axis field on items), skills.md row, docs/README.md Notable updates entry, CHANGELOG Unreleased entry — user-outcome-first, round-density claim (1.56x against the pre-registered 1.5x bar), both accepted costs stated as the reason the dial exists (3x tokens on clean diffs; round 2 shrinks not disappears), site cookbook named as pending downstream. All framed inside reviews-being-optional, positive formulation. Codex docs mirror synced.

Review trail (conductor-owned host reviews): round 1 NEEDS_WORK (8 — CHANGELOG honesty gap, cross-family constraint missing at three sites, 6 precision items), round 2 SHIP (all fixed; one non-blocking LOW recorded on host-pin wording). Full suite 4608 green at 3b182f5a; doc-pin suites + anchors green at 1e2b9265.

stage: impl-review - ran [2 rounds: NEEDS_WORK -> SHIP] (model: claude-fable-5 fresh subagents, conductor-owned)
stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 3b182f5a, 1e2b9265
- Tests: python3 scripts/run_tests_parallel.py (4608 OK at 3b182f5a), cd plugins/flow-next/tests && python3 -m unittest test_ralph_docs_truth test_review_findings_docs -q, python3 scripts/check_doc_anchors.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh x2 idempotent
- PRs: