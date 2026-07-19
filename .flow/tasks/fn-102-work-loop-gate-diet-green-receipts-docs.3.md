---
satisfies: [R5, R6]
---

## Description

Docs, glossary, changelog, the fn-83 boundary addendum, and the live R6 measurement proof.

**Size:** S
**Files:** `plugins/flow-next/docs/flowctl.md`, `GLOSSARY.md`, `CHANGELOG.md`, `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md`, codex mirror (docs not mirrored - verify)

1. `docs/flowctl.md`: new `### gate` section on the triage-skip template (usage, exit codes 0/1/2+, receipt JSON schema, 24h TTL, fail-closed matrix, the two-whitelists-two-purposes note); add `gate` to the top-of-file command list.
2. `GLOSSARY.md`: new `Green receipt` term (one dense paragraph, relates_to `Triage skip`, `Receipt`); clarify the existing `Receipt` entry scopes to review receipts.
3. `CHANGELOG.md`: `## Unreleased` entry (batched release - NO version bump, no bump.sh): faster work loop, `flowctl gate` group, loud-skip evidence convention, fn-89 post-mortem motivation.
4. fn-83 decision record: one-line forward-pointer addendum under Prevention ("fn-102's hash/path-only gate diet is outside this ban - predicates are commit-hash equality + path membership, no semantic proxies; see fn-102 Decision Context").
5. R6 live proof (evidence-only, record measurements in this task's evidence): (a) docs-only probe - stage a trivial docs diff on a scratch branch, run the classify + tier-B path, show zero full-suite executions + GATE_SKIPPED lines; (b) receipt probe - run the full suite once, write receipt, run `gate check` -> exit 0, then dirty a code file -> exit 1 (fail-closed demonstrated live); (c) confirm zero green->red regressions (full suite green at task end). Timing notes for the follow-up post-mortem comparison.

## Acceptance
- [ ] R5: fn-83 record addendum in place; docs state the scope guard
- [ ] R6: live proof recorded with measurements; fail-closed demonstrated; suite green at end

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
