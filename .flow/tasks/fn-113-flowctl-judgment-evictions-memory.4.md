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
Split-by-mode shipped exactly per the interview decision: the three existing autonomy markers (FLOW_RALPH=1 / REVIEW_RECEIPT_PATH set / FLOW_AUTONOMOUS=1 - reused, none invented; empty REVIEW_RECEIPT_PATH is not a marker) gate the deterministic path - verdict-flip thresholds, fingerprint confidence promotion, validator receipt mutation - with receipts proven byte-identical to a frozen golden fixture both via the apply helpers and end-to-end through _run_deep_pass under FLOW_RALPH=1. Interactive impl-review surfaces raw findings/decisions with host_judges: true and never mutates the seed receipt (read_bytes-unchanged assertions). Consolidated CHANGELOG Unreleased rider covers all four fn-113 tasks. Host review closed the delegate's flagged prose lag (impl-review optional-phases.md Step D.4 now documents both modes) and fixed two smoke-harness pins the task lists missed: the memory high-overlap case re-pinned to created+matches with an explicit --update mutation leg, and the validator no-op smoke now exports FLOW_AUTONOMOUS=1 (receipt mutation is the autonomous path by design). Final gates: full parallel suite 85 files / 1852 tests / 0 failures / 70.9s; smoke_test.sh All tests passed (136 checks); ci_test.sh 67/67; focused review suites 244 green; dual-copy identical; sync-codex x2.
## Evidence
- Commits: d4f78542450550ed27d5799d4b543d83cb761df1
- Tests: python3 scripts/run_tests_parallel.py (85 files, 1852 tests, 0 failures, 70.9s), bash smoke_test.sh (All tests passed, 136 checks), bash ci_test.sh (67/67), receipt byte-identity fixture: helpers + end-to-end under FLOW_RALPH=1, interactive no-mutation: read_bytes-unchanged assertions
- PRs: