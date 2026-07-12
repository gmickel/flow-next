---
satisfies: [R19]
---

## Description
The `flowctl prime classify --json` emitter + synthetic-fixture CI oracle (resolution 19, two-oracle split).

**Size:** M | **Files:** `plugins/flow-next/scripts/flowctl.py` AND `.flow/bin/flowctl.py` (byte-identical dual-copy invariant - update BOTH), `plugins/flow-next/tests/test_prime_eval.py`, `.github/workflows/test-flow-next.yml` (add the new test file to the explicit list), fixture-builder module under `plugins/flow-next/tests/`

## Approach
- Emitter: pure-stdlib deterministic probes - axes 1-4 raw signals (lifecycle counters, topology bits + workspace dampener inputs, size/exclusion-filtered LOC + legibility sub-signals, manifest-gated stack detection), shape MARKERS (not final shapes - judgment is skill-side), and the deterministic substance greps (hook classification inputs, env cross-ref counts, destructive-scan raw hits with context class). Schema per classification.md (task 2). `--json` threads; bounded; portable (no bare timeout binary; POSIX classes).
- Redaction contract: evidence carries key names only, never secret values or complete sensitive config lines; a fixture asserts it.
- Fixture builders: temp git-init repos (never in-tree .git): workspace-parent, tier-a siblings, tier-b home base, greenfield, greenfield-x-constellation, worktree-sibling.
- CI oracle: unittest drives the emitter over the fixtures asserting RAW signals/markers/exclusions only (per-row over the expectation table); wire test_prime_eval.py into the workflow's explicit test list; parity test asserts the two flowctl copies stay byte-identical; one live-subcommand smoke (`prime classify --json` on a fixture).

## Key context
- Judgment outputs (final shapes, confidence, asks) are OUT of scope here - the non-CI agentic eval (task 11) owns those.
- unittest not pytest; 3-OS matrix portability.

## Acceptance
- [ ] Emitter in BOTH flowctl copies, parity-tested, live-subcommand test passes (resolution 19)
- [ ] Raw-signal schema matches classification.md; --json threads; redaction fixture green
- [ ] Six fixture builders + expectation table as data rows; CI oracle asserts signals/markers/exclusions only
- [ ] test_prime_eval.py wired into .github/workflows/test-flow-next.yml explicit list; suite green on the emitter tests

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
