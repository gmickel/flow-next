---
satisfies: [R1, R2, R3, R4, R5]
---

## Description

Single cohesive task: the ancestor-walk in `gate check`, the capture rule in worker.md, the test class, and the doc trues-up. All contracts are in the parent spec R1-R5 - implement them verbatim; the spec's Decision Context carries the verified line anchors.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` + `.flow/bin/flowctl.py` (dual-copy, byte-identical, committed together), `plugins/flow-next/agents/worker.md`, `plugins/flow-next/tests/test_gate_receipt.py`, `plugins/flow-next/docs/flowctl.md`, `GLOSSARY.md`, `CHANGELOG.md`, codex mirror (regen)

1. flowctl: implement R1's ancestor-walk in `cmd_gate_check` (anchors: exact-HEAD lookup at ~27641; insertion at the is_file() miss branch ~27654; glob GATE_RECEIPTS_DIR ~27334 for `*-<gate_id>.json`; reuse `_gate_ignored_worktree_path` ~27482 for the walk-diff paths; inline gate-section subprocess style with try/except OSError; TWO-dot diff, never the three-dot form classify uses). Deterministic newest-first by embedded timestamp, cap 8, short-circuit on honor, skip-never-abort on malformed/symlink/sha-mismatch/git-odd candidates, fall into the EXISTING schema/command/dirty/age checks (reuse, no duplication).
2. worker.md: R2's capture rule stated once, applied at Baseline (~L52), Verify (~L390), and the delegation verify flow (~L162); sweep for any other run-and-observe site.
3. Tests: R3's `GateReceiptAncestorWalkTestCase` matrix exactly as specified.
4. Docs: flowctl.md gate prose + exit table OR-branch; GLOSSARY Green receipt ancestor clause; CHANGELOG Unreleased entry with R4's honest framing (2.18.0 receipt path was structurally dead - 0/3 honored in the fn-103 trace - fixed here; ~35% floor recorded as measured, not promised).
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
