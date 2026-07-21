# fn-113-flowctl-judgment-evictions-memory.4 Deep-pass/validator split-by-mode + docs + rider

## Description
Deep-pass/validator split-by-mode (maintainer decision) + docs + CHANGELOG + full gate.

**Size:** M
**Files:** both flowctl.py copies, tests, plugins/flow-next/docs/flowctl.md + orchestration.md, CHANGELOG.md

### Approach

- MAINTAINER DECISION (in the spec, item 4): SPLIT BY MODE. Autonomous contexts keep the deterministic schema-checked path exactly as-is: _apply_deep_passes_to_receipt verdict-flip thresholds, fingerprint confidence promotion, validator receipt mutation. Interactive impl-review does NOT run flowctl's merge/promotion math - it surfaces the raw findings (validated/deep JSON) and the HOST judges.
- Mode detection: reuse the existing autonomous signals (FLOW_RALPH / REVIEW_RECEIPT_PATH / FLOW_AUTONOMOUS - locate the established detection used by make-pr/pilot; do NOT invent a new signal). Default (interactive): math off, findings surfaced verbatim with a one-line note that the host judges. Autonomous: unchanged behavior, receipts identical.
- Tests: autonomous-path receipts byte-identical (fixture); interactive path emits raw findings without receipt mutation.
- Docs: flowctl.md deep-pass/validator section documents the split; orchestration.md one line.
- CHANGELOG [Unreleased] rider for the whole fn-113 spec (all four tasks; register-conformant, no em dashes).
- Full gate for the spec: full parallel suite + smoke_test.sh + ci_test.sh (host re-runs; leave green).

### Acceptance

- [ ] Autonomous receipts byte-identical (fixture-proven); interactive surfaces raw findings, no flowctl merge/promotion
- [ ] Docs + consolidated CHANGELOG rider present
- [ ] Focused: test_backend_spec.py + review suites green; full suite green

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
