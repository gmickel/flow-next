---
satisfies: [R4, R5]
---
# fn-191-flowctl-review-terminal-machinery.3 Zero-behavior verification, docs, plan-sync, and the full gate

## Description
Prove the extraction changed nothing observable, update the docs that describe module layout and propagation, run plan-sync for the anchor churn this change causes, and take the full gate. No version bump (batched release decision).

**Size:** S/M
**Files:** `plugins/flow-next/docs/flowctl.md` (layout + propagation recipe), `plugins/flow-next/docs/architecture.md` (review-bookkeeping pointer), `agent_docs/local-dev.md` (propagation + integrity recipe), root `CLAUDE.md` (final-gate propagation command), `CHANGELOG.md`
**Touches:** [plugins/flow-next/docs/**, agent_docs/local-dev.md, CLAUDE.md, CHANGELOG.md]

### Approach
- **Zero-behavior evidence, not assertion:** diff the CLI surface deliberately - a representative set of subcommands' `--help` output, JSON shapes, and exit codes captured before and after on the same inputs. Record what was compared. The white-box suites must pass against the new import path WITHOUT being weakened; if any needed an edit, say exactly which and why in the summary (an easier test after a move is a regression, per G2).
- Docs: describe the new package in the layout tree, extend the propagation recipe, cross-link from the review-bookkeeping section. Remember the docs trees here are test-pinned and classified docs-only by the local gate classifier - run the full suite even though the tier says lint-only (the project instruction file states this).
- **Anchor churn:** this change shifts coordinates in every artifact that referenced the moved region. Run plan-sync after landing, and name the affected open specs in the change entry so the next reader does not read rotted anchors as a defect.
- CHANGELOG under `## Unreleased`, outcome-first: lead with what stops going wrong (a fix landing on one review path while its sibling stays wrong), then the mechanism. Explicitly state the bound - one subsystem, roughly a twentieth of the module, no startup claim, navigation payoff arrives with later extractions.
- Full gate: `python3 scripts/run_tests_parallel.py` with the exit code captured directly, plus `uvx ruff@0.16.0 check .`.

### Acceptance
- [ ] Before/after CLI surface comparison recorded (subcommand help output, JSON shapes, exit codes); no diffs
- [ ] White-box lock/reservation/epoch/atomicity tests pass against the new import path with no weakening; any test edit justified explicitly in the summary
- [ ] Docs updated: layout tree, propagation recipe, review-bookkeeping cross-link, local-dev recipe, root instruction-file gate command
- [ ] plan-sync run after landing; affected open specs named in the change entry alongside the anchor-churn note
- [ ] `## Unreleased` CHANGELOG entry, outcome-first, stating the one-subsystem bound and making no startup claim; no version bump
- [ ] Full suite + ruff green with exit codes captured directly; OS smoke matrix green

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
