---
satisfies: [R1, R2, R3, R4, R5]
---

## Description

Single cohesive task: the ancestor-walk in `gate check`, the capture rule in worker.md, the test class, and the doc trues-up. All contracts are in the parent spec R1-R5 - implement them verbatim; the spec's Decision Context carries the verified line anchors.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` + `.flow/bin/flowctl.py` (dual-copy, byte-identical, committed together), `plugins/flow-next/agents/worker.md`, `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md` (template verify clause), `plugins/flow-next/tests/test_gate_receipt.py`, `plugins/flow-next/docs/flowctl.md`, `GLOSSARY.md`, `CHANGELOG.md`, codex mirror (regen)

1. flowctl: implement R1's ancestor-walk in `cmd_gate_check` per the spec's STRUCTURE ruling: extract the PURE validator `_gate_receipt_valid(receipt, head_sha, command)` (schema/fingerprint/age/identity) + the separate walk helper `_gate_walk_candidate_ok(receipt_path, receipt, repo_root, head_sha)` (40-hex regex on embedded head_sha, OID canonicalization via rev-parse --verify <sha>^{commit} == embedded value, sha8 consistency, symlink, ancestry, two-dot ignore-set diff) per spec R1; both paths consume the validator, walk adds the helper - exact path byte-equivalent behavior, same reasons/exit taxonomy; worktree cleanliness checked ONCE per invocation (exit-2 taxonomy for real git-status failures preserved). Walk: glob GATE_RECEIPTS_DIR for `*-<gate_id>.json`, timestamp-DESC + filename tie-break sort (drop unparseable/naive timestamps pre-rank), cap 8, short-circuit, skip-never-abort. `gate receipt` gains best-effort prune-on-write of >24h receipts (silent on prune failure, never blocks the write). Anchors: lookup ~27641, miss branch ~27654, GATE_RECEIPTS_DIR ~27334, `_gate_ignored_worktree_path` ~27482; inline gate-section subprocess style; TWO-dot diff (never classify's three-dot).
2. worker.md: R2's capture rule stated once, applied at Baseline (~L52) + Verify (~L390) with the delegated-tasks-route-through-Verify sentence AND the gate Foreground rule (one blocking foreground Bash call, explicit 600s timeout, never run_in_background+monitor - the 2.5.3 review Foreground rule applied to gate runs); codex-delegation.md's fixed template verify slot gains the exit-code-observation clause. Sweep both files for other run-and-observe sites.
3. Tests: R3's `GateReceiptAncestorWalkTestCase` matrix exactly as specified, PLUS tied-timestamp deterministic-order case, prune-on-write case (old deleted, fresh kept), and three identity regressions: receipt with head_sha="HEAD" -> skipped; abbreviated-sha receipt -> skipped; sha of a non-commit object (tag/tree) -> skipped. Quick commands verbatim from spec R3.
4. Docs: flowctl.md gate prose + exit table OR-branch (+ prune-on-write note); GLOSSARY Green receipt ancestor clause; CHANGELOG Unreleased entry with R4's honest framing. Downstream handoff recorded in done summary: flow-next.dev gate/Green-receipt vocabulary update rides the landing workstream (separate repo).
5. Gates: full suite green pre+post (honor receipts/classify per the wired discipline); sync-codex x2 idempotent, guards green; dual-copy verified via cmp.

## Acceptance
- [ ] R1: walk implemented per spec (deterministic policy, cap 8, skip-never-abort, two-dot, shared predicate, per-candidate symlink + sha-consistency)
- [ ] R2: capture rule + gate Foreground rule at all suite-invocation sites; zero run-and-observe patterns, zero background+monitor gate runs remain
- [ ] R3: full test matrix green; existing exact-match tests untouched
- [ ] R4: CHANGELOG + docs carry the honest status; GLOSSARY updated
- [ ] R5: dual-copy identical; mirror idempotent x2; suite green

## Done summary
Implemented the fn-116 gate-diet follow-up: `gate check` now honors ancestor receipts via a deterministic bounded walk (pure validator + walk helper, timestamp-DESC/filename tie-break, cap 8, skip-never-abort, two-dot ignore-set diff, OID canonicalization) with prune-on-write in `gate receipt`; worker.md/codex-delegation.md gained the suite-output capture rule (exit-code observation, log capture, no re-runs) plus the R2-amended gate Foreground rule (one blocking foreground call, 600s timeout, never bg+monitor); 18 new tests (13-case named matrix + delayed-status TTL shim, FIFO/oversized/nested-JSON hostile-file regressions); docs/GLOSSARY/CHANGELOG updated with honest framing. Review (codex): r1 NEEDS_WORK (post-status TTL ordering, unbounded receipt loads) fixed, then SHIP; SHIP re-confirmed after the R2 amendment. Full suite green pre+post (1856 tests OK, suite_rc=0); mirror x2 idempotent; dual-copy byte-identical. Delegation: codex gpt-5.6-terra (high) wrote the initial implementation (honest partial - dual-copy/mirror host-owned); orchestrator finished locally. Downstream handoff for the lander: flow-next.dev gate/Green-receipt vocabulary needs the ancestor-clause update in ~/work/flow-next.dev in the landing workstream (fn-103 precedent).
## Evidence
- Commits: e755b597ed1eca1ac013faf0d39bf4dc1023c48e, 48fea21fbcd45c6fbc305387c3149ccf44e54974, c68efeaed46d460e392b07abc05a8c3266b6481a, 9aee55cfa3461d5254b54428754b9b7a3618fd8e
- Tests: baseline: green (cd plugins/flow-next/tests && python3 -m unittest discover -q; suite_rc=0, 1851 tests pre-edit), cd plugins/flow-next/tests && python3 -m unittest test_gate_receipt test_gate_classify -q (64 tests OK), cd plugins/flow-next/tests && python3 -m unittest discover -q (Ran 1856 tests, OK skipped=2, suite_rc=0; green receipt 9aee55cf-unittest written), ./scripts/sync-codex.sh x2 idempotent (identical mirror-diff sha256 snapshots), cmp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py (byte-identical)
- PRs: