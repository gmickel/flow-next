# fn-29-review-rigor-bundle.3 Confidence anchors + suppression gate

## Description

Add discrete 5-value confidence rubric (0/25/50/75/100) to review prompts. Suppress findings below anchor 75 except P0 findings at 50+. Report `suppressed_count` by anchor.

**Size:** S (prompt-only)

**Files:**
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md`
- `plugins/flow-next/skills/flow-next-epic-review/workflow.md`
- `plugins/flow-next/agents/quality-auditor.md` (quality-auditor also emits findings; same rubric)

## Change details

### Review prompts (impl-review + epic-review)

Add a "Confidence calibration" section to the review prompt, before the findings format:

```markdown
## Confidence calibration

Rate each finding on exactly one of these 5 discrete anchors. Do not use interpolated values (no 33, 80, 90).

| Anchor | Meaning |
|--------|---------|
| 100 | Verifiable from the code alone, zero interpretation. A definitive logic error (off-by-one in a tested algorithm, wrong return type, swapped arguments, clear type error). The bug is mechanical. |
| 75 | Full execution path traced: "input X enters here, takes this branch, reaches line Z, produces wrong result." Reproducible from the code alone. A normal caller will hit it. |
| 50 | Depends on conditions visible but not fully confirmable from this diff — e.g., whether a value can actually be null depends on callers not in the diff. Surfaces only as P0-escape or via soft-bucket routing. |
| 25 | Requires runtime conditions with no direct evidence — specific timing, specific input shapes, specific external state. |
| 0 | Speculative. Not worth filing. |

## Suppression gate

After all findings are collected:
1. Suppress findings below anchor 75.
2. **Exception:** P0 severity findings at anchor 50+ survive the gate. Critical-but-uncertain issues must not be silently dropped.
3. Report the suppressed count by anchor in a `Suppressed findings` section of the review output.

Example:

> Suppressed findings: 3 at anchor 50, 7 at anchor 25, 2 at anchor 0.
```

### Findings format

Each surviving finding in the review output carries a `confidence: <N>` field alongside severity, file, line:

```markdown
### Finding 1: [title]
- **Severity:** P1
- **Confidence:** 75
- **Location:** src/auth.ts:42
- **Classification:** introduced
- **Detail:** ...
- **Suggested fix:** ...
```

### quality-auditor.md agent

Add the same confidence calibration block. The quality-auditor runs post-task; its findings go through the same suppression logic. No separate receipt write — its output is consumed by the worker agent inline.

### flowctl receipt

Add optional `suppressed_count` field to the receipt schema (all three backends):

```python
if suppressed_count:  # dict {anchor: count}
    receipt_data["suppressed_count"] = suppressed_count
```

Parse from review output by scanning for the `Suppressed findings:` line.

## Rationale

Free-form confidence language ("probably", "might be", "definitely") produces fuzzy priority signals. MergeFoundry upstream's discrete 5-anchor rubric forces the reviewer to commit, and the gate turns the anchors into actionable filtering. Ralph benefits directly — fewer anchor-25 speculations in the fix loop.

## Acceptance

- **AC1:** impl-review and epic-review prompts contain the 5-anchor rubric verbatim.
- **AC2:** Quality-auditor agent uses the same rubric.
- **AC3:** Review output emits `Confidence: <0|25|50|75|100>` on every finding.
- **AC4:** Suppression gate drops <75 findings except P0 at 50+.
- **AC5:** Review output includes a `Suppressed findings:` summary when any were suppressed.
- **AC6:** Receipt optionally carries `suppressed_count: {anchor: count}` dict.
- **AC7:** Existing Ralph smoke tests pass.

## Out of scope

- Per-backend tuning (rp vs codex vs copilot) — same rubric applies uniformly.
- Quantitative validation that the gate improves signal (collect metrics post-ship).
- Cross-reviewer agreement promotion (requires multi-persona; see Epic 4 `--deep`).

## Done summary
Added 5-anchor confidence rubric (0/25/50/75/100) + suppression gate to impl-review, epic-review, and standalone review prompts across rp/codex/copilot backends; quality-auditor agent mirrors the same rubric. Receipts now optionally carry `suppressed_count` (parsed via `parse_suppressed_count` helper in flowctl.py + awk splice in RP workflow.md files); smoke suite gains targeted regression coverage.
## Evidence
- Commits: cdfd42c403e6c936dda74a8a88714c98632f282c
- Tests: plugins/flow-next/scripts/smoke_test.sh (68 passed, 0 failed)
- PRs: