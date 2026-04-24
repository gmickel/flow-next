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

<!-- Updated by plan-sync: fn-32.1 added `kept`, `verdict_before_validate`, and `validator_timestamp` fields alongside the validator block. Upgrade path only runs NEEDS_WORK → SHIP; never downgrades. -->
<!-- Updated by plan-sync: fn-32.2 added `cross_pass_promotions`, `verdict_before_deep`, and `deep_timestamp` alongside `deep_passes`/`deep_findings_count`. Deep-pass verdict path is SHIP → NEEDS_WORK only (upgrade in stringency); never downgrades. -->
<!-- Updated by plan-sync: fn-32.3 walkthrough block also carries `lfg_rest` (bool) alongside `applied/deferred/skipped/acknowledged`; receipt also gains `walkthrough_timestamp`. Walkthrough never flips verdict — sorts findings only. New helpers `flowctl review-walkthrough-defer` (appends to `.flow/review-deferred/<branch-slug>.md`) and `flowctl review-walkthrough-record` (stamps receipt counts) do the I/O. Branch slug keeps `_` and `.` in addition to `a-zA-Z0-9-`. -->

Add a schema check (or unit test) that verifies:

1. Default review (no flags) produces receipt with only base fields (no validator, deep_passes, walkthrough).
2. Each flag adds exactly its own field without mutating others. The `--validate` path also writes `validator_timestamp` (always) and `verdict_before_validate` (only when the verdict was upgraded from NEEDS_WORK → SHIP). The `--deep` path also writes `deep_timestamp` (always), `deep_findings_count` (per-pass dict), `cross_pass_promotions` (list of `{id, from, to, pass}`), and `verdict_before_deep` (only when the verdict was upgraded from SHIP → NEEDS_WORK by deep-pass findings). The `--interactive` path writes `walkthrough: {applied, deferred, skipped, acknowledged, lfg_rest}` + `walkthrough_timestamp`; verdict is never flipped by walkthrough.
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
    # validator block carries dispatched/dropped/kept/reasons (kept added in fn-32.1)
    assert set(receipt["validator"].keys()) >= {"dispatched", "dropped", "kept", "reasons"}
    assert "validator_timestamp" in receipt
    assert "deep_passes" not in receipt

def test_receipt_with_validate_all_dropped_upgrade():
    # When all findings drop and prior verdict was NEEDS_WORK, verdict upgrades to SHIP
    # and `verdict_before_validate` is recorded.
    receipt = run_review_with_flags(["--validate"], force_all_dropped=True)
    assert receipt["verdict"] == "SHIP"
    assert receipt["verdict_before_validate"] == "NEEDS_WORK"

def test_receipt_with_deep():
    receipt = run_review_with_flags(["--deep"])
    assert "deep_passes" in receipt
    assert "deep_findings_count" in receipt
    assert "cross_pass_promotions" in receipt  # list (may be empty)
    assert "deep_timestamp" in receipt
    assert "validator" not in receipt

def test_receipt_with_deep_ship_to_needs_work_upgrade():
    # When primary verdict is SHIP but deep-pass surfaces a new blocking
    # `introduced` finding, verdict upgrades SHIP → NEEDS_WORK and
    # `verdict_before_deep` is recorded. Deep never downgrades the verdict.
    receipt = run_review_with_flags(["--deep"], force_deep_blocking=True)
    assert receipt["verdict"] == "NEEDS_WORK"
    assert receipt["verdict_before_deep"] == "SHIP"

def test_receipt_all_flags():
    receipt = run_review_with_flags(["--validate", "--deep"])  # --interactive not auto-testable
    assert "validator" in receipt
    assert "deep_passes" in receipt
    assert "deep_findings_count" in receipt
    assert "cross_pass_promotions" in receipt
    assert "verdict" in receipt

def test_receipt_with_walkthrough_shape():
    # --interactive can't be fully auto-tested (needs blocking tool), but the
    # receipt shape written by `flowctl review-walkthrough-record` is stable:
    # walkthrough carries applied/deferred/skipped/acknowledged/lfg_rest + a
    # walkthrough_timestamp, and verdict is never flipped by walkthrough.
    receipt = simulate_walkthrough_record(applied=2, deferred=1, skipped=0, acknowledged=0, lfg_rest=False)
    assert set(receipt["walkthrough"].keys()) == {"applied", "deferred", "skipped", "acknowledged", "lfg_rest"}
    assert "walkthrough_timestamp" in receipt
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

- **--validate with no primary findings**: validator still writes a validator block with `dispatched=0, dropped=0, kept=0, reasons=[]` plus `validator_timestamp`; verdict unchanged. (Implementation writes the empty block rather than omitting the field — keeps receipt shape deterministic for consumers.)
- **--validate with no session_id in receipt**: validator errors with exit 2 (cannot resume session).
- **--validate across backends (e.g. codex primary, copilot validator)**: validator errors with exit 2 (session continuity guard — receipt `mode` must match validator backend).
- **--validate with unknown finding ids in validator output**: treated as `kept` (conservative default).
- **--deep with no applicable passes (no auto-match + no explicit list)**: runs adversarial only (adversarial is always selected when `--deep` is set; skill uses `flowctl review-deep-auto` against the changed-file list to add security/performance when they match globs).
- **--deep with primary SHIP + new blocking deep finding**: verdict upgrades SHIP → NEEDS_WORK; `verdict_before_deep == "SHIP"` recorded. Deep never downgrades (no NEEDS_WORK → SHIP path).
- **--deep with primary finding and deep finding sharing a fingerprint**: primary wins (deep drops) and primary's confidence is promoted one anchor step (0→25→50→75→100; ceiling 100). Promotion is recorded in `cross_pass_promotions` as `{id, from, to, pass}`. Cross-deep collisions dedup without promotion (avoids double-counting correlated passes).
- **--interactive with only pre-existing findings**: walk through still happens but Apply list is likely empty (pre-existing usually Skipped)
- **--validate drops all findings**: verdict upgrades to SHIP only when prior verdict was `NEEDS_WORK` (never downgrades from SHIP or MAJOR_RETHINK); `validator.kept == 0`, `validator.dropped == dispatched`, `verdict_before_validate == "NEEDS_WORK"` recorded.
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
