---
satisfies: [R5, R6]
---

## Description

Docs, glossary, changelog, fn-83 boundary addendum, and the R6 PRE-LAND end-to-end proof.

**Size:** M
**Files:** `plugins/flow-next/docs/flowctl.md`, `GLOSSARY.md`, `CHANGELOG.md`, `.flow/memory/knowledge/decisions/plan-sync-skip-gate-not-viable-2026-07-03.md`

1. `docs/flowctl.md`: new `### gate` section on the triage-skip template (usage incl. --command fingerprint, exit codes 0/1/2+, receipt JSON schema, 0<=age<=24h TTL, cleanliness ignore-set, fail-closed matrix, the two-whitelists-two-purposes note); add `gate` to the top-of-file command list.
2. `GLOSSARY.md`: new `Green receipt` term (relates_to `Triage skip`, `Receipt`); clarify `Receipt` scopes to review receipts.
3. `CHANGELOG.md`: `## Unreleased` entry (batched - NO bump.sh).
4. fn-83 decision record: one-line forward-pointer addendum under Prevention ("fn-102's hash/path-only gate diet is outside this ban - predicates are commit-hash equality + path membership + receipt age, no semantic proxies").
5. R6 pre-land proof, in a scratch worktree on the implementation branch (evidence-only; instrumented by COUNTING suite invocations): (a) docs-only probe - scratch docs diff through the wired Verify-site decision -> tier-B, GATE_SKIPPED lines, ZERO suite executions counted; (b) receipt probe - suite run once, receipt written via the wired command, `gate check` same command -> exit 0; then EACH of {dirtied code file, changed command string, future-timestamp receipt} -> exit 1 (fail-closed live); (c) full suite green at branch tip. Record counts + outcomes in evidence. Post-land trace post-mortem (gate share <= 50% of fn-89 baseline) is a tracked follow-up, NOT acceptance here.

## Acceptance
- [ ] R5: fn-83 record addendum in place; docs state the scope guard
- [ ] R6: pre-land proof recorded with counts; three fail-closed flips demonstrated; suite green at tip

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
