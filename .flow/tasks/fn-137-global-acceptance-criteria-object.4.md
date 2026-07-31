---
satisfies: [R5, R4]
---
# fn-137-global-acceptance-criteria-object.4 Docs, G-ID grammar, full gate

## Description
Documentation + convergence.

**Size:** S

### Approach
- Docs: G-ID grammar documented beside the R-ID grammar (GLOSSARY + the spec-template/docs pages that define R-IDs), memory-schema/receipts compliance field, teams.md standing-criteria note, setup docs; GLOSSARY 'global criteria (G-ID)' entry references the downstream-consumers strategy note from fn-136.
- Unreleased CHANGELOG (repo + docs-site walk note); no version bump.
- Full suite + smoke where touched.

## Acceptance
- [ ] Docs complete incl. G-ID beside R-ID; Unreleased entries; full gate green (R5, R4).

## Done summary
Documented the fn-137 global-criteria feature across every doc surface: G-ID grammar beside the R-ID rules (GLOSSARY.md new "Global criterion (G-ID)" entry referencing the fn-136 flow-swarm-preparation strategy note, spec-template.md new Global-criteria section), the additive completion-review receipt field `criteria: [{id, status, note?}]` (review-findings.md new section, memory-schema.md pointer, flowctl.md receipt example), a teams.md "Standing criteria" section (spec = unit of compliance, completion review sole surface, user-owned opt-in file), the flowctl.md `criteria list` / `criteria prompt-block` CLI reference plus .flow tree + command-index entries, a docs/README Notable-updates entry for the setup opt-in scaffold, and a user-outcome-first Unreleased CHANGELOG entry (no version bump). Full gate green: 3477 tests + ruff clean; sync-codex x2 idempotent with zero mirror diff.
## Evidence
- Commits: 81fc86e9bcf4be8a64ebd870ae76d4c3db695423, 99b48fa8
- Tests: baseline: none (spec defines no Quick commands; docs-only task), python3 scripts/run_tests_parallel.py (165 files, 3477 tests, 0 failures; first run had 1 known load-sensitive p95 perf flake in test_pr_cognitive_aid, green serially and on full re-run; GREEN_RECEIPT 81fc86e9-unittest), uvx ruff@0.16.0 check . (All checks passed), ./scripts/sync-codex.sh x2 (idempotent, zero mirror diff - docs/ not mirrored), post-review: python3 -m unittest test_review_findings_docs test_criteria -q (OK)
- PRs: