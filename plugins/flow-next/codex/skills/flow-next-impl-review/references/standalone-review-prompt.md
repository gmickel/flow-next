<!-- placeholders: base_branch, context_guidance, focus_section, diff_summary, smell_baseline_block, r_id_coverage_block, confidence_rubric_block, classification_rubric_block, protected_artifacts_block -->
# Implementation Review: Branch Changes vs {base_branch}

Review all changes on the current branch compared to {base_branch}.
{context_guidance}{focus_section}
## Diff Summary
```
{diff_summary}
```

## Review Criteria (Carmack-level)

1. **Correctness** - Does the code do what it claims?
2. **Reliability** - Can this fail silently or cause flaky behavior?
3. **Simplicity** - Is this the simplest solution?
4. **Security** - Injection, auth gaps, resource exhaustion?
5. **Edge Cases** - Failure modes, race conditions, malformed input?

## Scenario Exploration (for changed code only)

Walk through these scenarios for new/modified code paths:
- Happy path: Normal operation with valid inputs
- Invalid inputs: Null, empty, malformed data
- Boundary conditions: Min/max values, empty collections
- Concurrent access: Race conditions, deadlocks
- Network issues: Timeouts, partial failures
- Resource exhaustion: Memory, disk, connections
- Security attacks: Injection, overflow, DoS vectors
- Data corruption: Partial writes, inconsistency
- Cascading failures: Downstream service issues

Only flag issues in the **changed code** - not pre-existing patterns.

## Verdict Scope

Your VERDICT must only consider issues in the **changed code**:
- Issues **introduced** by this changeset
- Issues **directly affected** by this changeset
- Pre-existing issues that would **block shipping** this specific change

Do NOT mark NEEDS_WORK for:
- Pre-existing issues in untouched code
- "Nice to have" improvements outside the diff
- Style nitpicks in files you didn't change

You MAY mention these as "FYI" observations without affecting the verdict.
{smell_baseline_block}
{r_id_coverage_block}
{confidence_rubric_block}
{classification_rubric_block}
{protected_artifacts_block}
## Output Format

For each surviving `introduced` finding:
- **Severity**: Critical / Major / Minor / Nitpick (P0 / P1 / P2 / P3 accepted)
- **Confidence**: 0 / 25 / 50 / 75 / 100 (one of the five discrete anchors)
- **Classification**: introduced
- **File:Line**: Exact location
- **Problem**: What's wrong
- **Suggestion**: How to fix

Then, under a separate `## Pre-existing issues (not blocking this verdict)` heading, list each `pre_existing` finding as `[severity, confidence N, introduced=false] file:line — summary`. Never silently drop pre-existing findings.

After the findings list, emit:
- The `## Requirements coverage` table and `Unaddressed R-IDs:` line (only when the spec uses R-IDs; otherwise skip).
- A `Suppressed findings:` line tallying anchors dropped by the gate (omit when nothing was suppressed).
- A `Classification counts:` line tallying `introduced` vs `pre_existing` survivors, e.g. `Classification counts: 2 introduced, 4 pre_existing.`.
- A `Protected-path filter:` line tallying findings dropped by the protected-path filter (omit when nothing was dropped).

Be critical. Find real issues.

**Verdict gate:** only `introduced` findings affect the verdict. A review whose sole surviving findings are all `pre_existing` MUST ship. Any non-deferred `not-addressed` R-ID also forces NEEDS_WORK regardless of other findings.

**REQUIRED**: End your response with exactly one verdict tag:
- `<verdict>SHIP</verdict>` - Ready to merge (no blocking `introduced` findings, all R-IDs met or deferred)
- `<verdict>NEEDS_WORK</verdict>` - `introduced` issues or unaddressed R-IDs must be fixed first
- `<verdict>MAJOR_RETHINK</verdict>` - Fundamental problems, reconsider approach
