---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-292-avoid-caching-failed-fallback-review.1 Cache only successful fallback executions and invalidate failed cached choices

## Description
Resolve the confirmed failed-fallback cache bug across the four review CLI adapters. Preserve the existing ladder, error, and receipt contracts; add mocked regressions and correct the public cache/floor description.

**Touches:** plugins/flow-next/scripts/flowctl.py, plugins/flow-next/tests/test_model_resolution.py, plugins/flow-next/docs/flowctl.md
**Satisfies:** R1, R2, R3, R4, R5

### Quick commands
- `PYTHONPATH=plugins/flow-next/tests python3 -m unittest test_model_resolution.TestFallbackCacheExecutionStatus`
- `PYTHONPATH=plugins/flow-next/tests python3 -m unittest test_model_resolution`
- `python3 scripts/check_doc_anchors.py`
- `./scripts/sync-codex.sh --check`

## Acceptance
- [ ] R1: Cache writes and fallback-cache warnings require exit code 0 on every shared and Cursor-specific fallback path.
- [ ] R2: Failed cached choices are invalidated with terminal errors returned without same-call retry; existing bounded model-unavailability re-resolution remains.
- [ ] R3: Successful fallback behavior, explicit pins, cache identity/TTL, lazy version lookup, bounded steps, receipts, and review-cap paths remain intact.
- [ ] R4: Mocked tests cover all four adapters, exact dispatch order/exit result, cache and diagnostic state, and the next invocation; no provider calls.
- [ ] R5: Public docs describe a fallible CLI-default floor and exit-zero cache eligibility while preserving the heading anchor.

### Validation notes
- The isolated focused test command first ran red against the unchanged dispatcher.
- The coordinator owns generated mirrors, the full offline suite, and independent official review gates.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
