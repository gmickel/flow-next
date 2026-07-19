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
Documented the fn-102 gate diet (new `### gate` section in docs/flowctl.md with exit codes, receipt schema, TTL, ignore-set, fail-closed matrix and the two-whitelists note; `Green receipt` glossary term with `Receipt` scoped to review receipts; Unreleased CHANGELOG entry; fn-83 decision-record scope-note addendum) and ran the R6 pre-land proof in a scratch worktree at branch tip: docs-only probe hit tier-B with zero suite executions, the receipt probe honored a green receipt then flipped to exit 1 on each of dirtied-code-file / changed-command / future-timestamp, and the full suite is green at tip (1818 OK). Docs implementation delegated to codex gpt-5.6-terra (medium); review resolved via deterministic triage-skip SHIP.
## Evidence
- Commits: 19a70b97a4ea392b1217ae4a9dd9cd774b44f4c5, 49df33fd855a48a0cacbc4b97a16e441a5d4a131
- Tests: baseline: green (gate check --gate unittest probe first: exit 1 'no receipt for HEAD' -> ran full; python3 -m unittest discover -s plugins/flow-next/tests -q -> Ran 1818 tests, OK (skipped=2), exit 0, pre-edit at 82ba0ae6; run twice - first run's exit code lost to a pipe, captured re-run recorded), gate classify --base 82ba0ae6 (Verify site) -> tier-b, exit 0: 4 paths all safe (.flow/memory decision .md, CHANGELOG.md, GLOSSARY.md, plugins/flow-next/docs/flowctl.md); tier-B gate set ran (no repo-configured md lint), suite/smoke not invoked, GATE_SKIPPED:unittest:docs-only - cumulative diff classified tier-B (no executable paths touched), GATE_SKIPPED:smoke:docs-only - cumulative diff classified tier-B (no executable paths touched), R6(a) docs-only probe (scratch worktree, detached @49df33fd, fresh .flow/tmp - per-checkout receipt scoping confirmed): scratch untracked agent_docs/*.md diff -> gate classify --base HEAD exit 0 TIER_B: docs-only (1 files); full-suite executions counted during probe: 0, R6(b) receipt probe (same worktree): python3 -m unittest discover -s plugins/flow-next/tests -q -> Ran 1818 tests, OK (skipped=2), exit 0 (suite executions counted: 1); gate receipt --gate unittest -> .flow/tmp/green-receipts/49df33fd-unittest.json, exit 0; gate check same command -> exit 0 HONORED; fail-closed flips: dirtied code file -> exit 1 (worktree dirty: probe_dirty.py); changed command string -> exit 1 (command fingerprint mismatch); future-timestamp receipt -> exit 1 (receipt timestamp in the future), R6(c) full suite green at branch tip 49df33fd: Ran 1818 tests, OK (skipped=2), exit 0 (same single run as R6(b); zero green->red regressions), codex batch verification: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_gate_*.py' -q (30 tests OK); grep checks for ### gate / command list / ## Green receipt / ## Unreleased all hit; added em dashes: 0, impl-review: deterministic triage-skip SHIP (mode=triage_skip, reason: release-chore/docs, base 82ba0ae6)
- PRs: