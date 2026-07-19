---
satisfies: [R1, R2, R3, R4, R5]
---

## Description

Single cohesive task: the ancestor-walk in `gate check`, the capture rule in worker.md, the test class, and the doc trues-up. All contracts are in the parent spec R1-R5 - implement them verbatim; the spec's Decision Context carries the verified line anchors.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` + `.flow/bin/flowctl.py` (dual-copy, byte-identical, committed together), `plugins/flow-next/agents/worker.md`, `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md` (template verify clause), `plugins/flow-next/tests/test_gate_receipt.py`, `plugins/flow-next/docs/flowctl.md`, `GLOSSARY.md`, `CHANGELOG.md`, codex mirror (regen)

1. flowctl: implement R1's ancestor-walk in `cmd_gate_check` per the spec's STRUCTURE ruling: extract the return-based validator `_gate_receipt_valid(...)` (schema/fingerprint/age common; exact-mode identity; ancestor-mode sha8-consistency + ancestry + two-dot diff) and have BOTH paths consume it - exact path byte-equivalent behavior, same reasons/exit taxonomy; worktree cleanliness checked ONCE per invocation (exit-2 taxonomy for real git-status failures preserved). Walk: glob GATE_RECEIPTS_DIR for `*-<gate_id>.json`, timestamp-DESC + filename tie-break sort (drop unparseable/naive timestamps pre-rank), cap 8, short-circuit, skip-never-abort. `gate receipt` gains best-effort prune-on-write of >24h receipts. Anchors: lookup ~27641, miss branch ~27654, GATE_RECEIPTS_DIR ~27334, `_gate_ignored_worktree_path` ~27482; inline gate-section subprocess style; TWO-dot diff (never classify's three-dot).
2. worker.md: R2's capture rule stated once, applied at Baseline (~L52) + Verify (~L390) with the delegated-tasks-route-through-Verify sentence; codex-delegation.md's fixed template verify slot gains the exit-code-observation clause. Sweep both files for other run-and-observe sites.
3. Tests: R3's `GateReceiptAncestorWalkTestCase` matrix exactly as specified, PLUS tied-timestamp deterministic-order case and a prune-on-write case (old receipt deleted, fresh kept). Quick commands verbatim from spec R3.
4. Docs: flowctl.md gate prose + exit table OR-branch (+ prune-on-write note); GLOSSARY Green receipt ancestor clause; CHANGELOG Unreleased entry with R4's honest framing. Downstream handoff recorded in done summary: flow-next.dev gate/Green-receipt vocabulary update rides the landing workstream (separate repo).
5. Gates: full suite green pre+post (honor receipts/classify per the wired discipline); sync-codex x2 idempotent, guards green; dual-copy verified via cmp.

## Acceptance
- [ ] R1: walk implemented per spec (deterministic policy, cap 8, skip-never-abort, two-dot, shared predicate, per-candidate symlink + sha-consistency)
- [ ] R2: capture rule at all suite-invocation sites; zero run-and-observe patterns remain
- [ ] R3: full test matrix green; existing exact-match tests untouched
- [ ] R4: CHANGELOG + docs carry the honest status; GLOSSARY updated
- [ ] R5: dual-copy identical; mirror idempotent x2; suite green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
