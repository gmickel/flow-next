---
satisfies: [R8, R9]
---
# fn-179-issue-batch-r-id-parser-straggler.5 Gate-classify docs statement, CHANGELOG credits, propagation + full gate

## Description
Spec fn-179 R8-R9. Docs: state the gate-classify path taxonomy is deliberately closed to config, per-repo gate policy belongs in the consumer's conductor instructions (pilot.gateClasses is the open vocabulary), reason strings are not a stable contract (promised on #313). CHANGELOG Unreleased entries crediting @sn-furali per fixed issue. Dual flowctl copy propagation + tracker manifest + sync-codex twice + full suite + ruff pinned.

## Acceptance
R8, R9 of the spec. Full gate green; no version bump (batched releases).

## Done summary
R8-R9 closed out. flowctl.md gate-classify section now states the taxonomy is deliberately closed to config (misconfigured taxonomy would silently skip gates), per-repo gate policy belongs in the consumer's conductor instructions with pilot.gateClasses as the open vocabulary, and reason strings are diagnostics, not a stable contract (#313 answer, to be posted on the issue). Worker-flagged doc lines landed: start --reclaim (flags, gate semantics, note wordings), tracker resolve --select (union, CONFLICT-unstamped, in_review never auto-fills), platforms.md CLAUDE_PLUGIN_ROOT note tied to #306, make-pr coverage ratio surfaces acceptance_criteria_residue with a never-silent rule. CHANGELOG Unreleased credits @sn-furali per issue (#300 #303 #305 #306 #308 #316) plus the #313 docs entry. Full gate green; no version bump.
## Evidence
- Commits: 794df792
- Tests: python3 scripts/run_tests_parallel.py (4385 OK, 0 failures), uvx ruff@0.16.0 check . (clean), ./scripts/sync-codex.sh x2 (idempotent)
- PRs: