# fn-32-opt-in-review-flags.4 Flag-combination interaction + receipt schema stability

## Description

Verify and implement correct behavior for all flag combinations. Ensure receipt schema remains additive and existing Ralph scripts read cleanly.

**Size:** S-M

**Files:**
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` — explicit phase ordering for combinations
- `plugins/flow-next/scripts/flowctl.py` — receipt writer schema check
- `.flow/bin/flowctl.py` (mirror)

## Phase ordering (explicit in workflow.md)

```
1. Primary review (always)
2. If --deep: run deep passes in same session → merge findings
3. If --validate: run validator pass on merged findings (or primary if no --deep)
4. If --interactive: walk through surviving findings
5. Verdict computed over surviving findings
6. Receipt written with all optional fields populated
```

Rationale:
- Deep runs before validate: deep produces more findings; validator filters the superset (more efficient)
- Validate runs before interactive: user walks through only validated findings (fewer decisions, higher quality)
- Interactive always last: consumes the fully-merged, fully-validated set

## Interaction matrix (documented)

| Combo | Phases |
|-------|--------|
| (default) | 1 → 5 → 6 |
| `--validate` | 1 → 3 → 5 → 6 |
| `--deep` | 1 → 2 → 5 → 6 |
| `--interactive` | 1 → 4 → 5 → 6 |
| `--validate --deep` | 1 → 2 → 3 → 5 → 6 |
| `--validate --interactive` | 1 → 3 → 4 → 5 → 6 |
| `--deep --interactive` | 1 → 2 → 4 → 5 → 6 |
| `--validate --deep --interactive` | 1 → 2 → 3 → 4 → 5 → 6 |

Receipt fields accumulate: each phase writes its own block without disturbing others.

## Receipt schema stability test

Add a schema check (or unit test) that verifies:

1. Default review (no flags) produces receipt with only base fields (no validator, deep_passes, walkthrough).
2. Each flag adds exactly its own field without mutating others.
3. All combinations produce receipts that pass existing Ralph gate logic (which reads `verdict`, `mode`, `session_id`).

Test pattern:

```python
def test_receipt_default():
    receipt = run_review_with_flags([])
    assert "validator" not in receipt
    assert "deep_passes" not in receipt
    assert "walkthrough" not in receipt
    assert "verdict" in receipt

def test_receipt_with_validate():
    receipt = run_review_with_flags(["--validate"])
    assert "validator" in receipt
    assert "deep_passes" not in receipt

def test_receipt_all_flags():
    receipt = run_review_with_flags(["--validate", "--deep"])  # --interactive not auto-testable
    assert "validator" in receipt
    assert "deep_passes" in receipt
    assert "verdict" in receipt
```

## Ralph compat test

After receipt extensions, run existing Ralph smoke:

```bash
plugins/flow-next/scripts/ralph_smoke_test.sh
```

Verify:
- Passes (no regression)
- Works with `FLOW_VALIDATE_REVIEW=1` (validator field appears in receipt but gate still satisfied)
- Works with `FLOW_REVIEW_DEEP=1` (deep_passes field appears but gate still satisfied)

## Edge cases

- **--validate with no primary findings**: skip validator (nothing to validate); receipt omits `validator` field
- **--deep with no applicable passes (no auto-match + no explicit list)**: runs adversarial only
- **--interactive with only pre-existing findings**: walk through still happens but Apply list is likely empty (pre-existing usually Skipped)
- **--validate drops all findings**: verdict upgrades to SHIP; `validator.dropped == dispatched`
- **Combination with --no-triage (from fn-29)**: triage-skip doesn't interact; if triage returns SKIP, none of these flags fire

## Acceptance

- **AC1:** Workflow.md documents the 8-row interaction matrix explicitly.
- **AC2:** Phase ordering (primary → deep → validate → interactive → verdict → receipt) is consistent across skill code and documentation.
- **AC3:** Receipt with no flags contains only base fields; no phantom empty objects for validator/deep_passes/walkthrough.
- **AC4:** Receipt with each flag alone adds exactly that flag's block.
- **AC5:** Receipt with combined flags accumulates blocks correctly.
- **AC6:** Ralph smoke tests pass with each env-var combination (FLOW_VALIDATE_REVIEW=1, FLOW_REVIEW_DEEP=1, both set).
- **AC7:** Unit tests cover receipt schema stability for all flag combinations.
- **AC8:** Edge cases documented and handled (empty findings, all-dropped, --interactive + pre-existing-only, triage-skip precedence).

## Dependencies

- fn-32-opt-in-review-flags.1 (--validate)
- fn-32-opt-in-review-flags.2 (--deep)
- fn-32-opt-in-review-flags.3 (--interactive)

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
