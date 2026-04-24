# fn-29-review-rigor-bundle.2 Per-R-ID coverage in impl-review + epic-review prompts

## Description

Extend review prompts so reviewers produce an explicit per-R-ID coverage table when a plan with R-IDs exists. Receipt carries `unaddressed: [R2, R5]`. Verdict flips to NEEDS_WORK on any unaddressed R-ID unless spec marks it deferred.

**Size:** M (prompt-only)

**Files:**
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md`
- `plugins/flow-next/skills/flow-next-epic-review/workflow.md`
- `plugins/flow-next/scripts/flowctl.py` (receipt schema — add `unaddressed` optional field to all three backends' receipt builders)
- `.flow/bin/flowctl.py` (mirror)

## Change details

### impl-review/workflow.md

Add a "Requirements Coverage" phase to the review prompt, **between current intent discovery and findings synthesis**:

```markdown
## Requirements Coverage (if spec has R-IDs)

If the task spec references an epic spec (`.flow/specs/fn-N-slug.md`), read the epic spec's `## Acceptance` (or legacy `## Acceptance criteria`) section and extract R-IDs. <!-- Updated by plan-sync: fn-29-review-rigor-bundle-r-ids-confidence.1 used `## Acceptance` heading in the plan-skill template (fn-29 epic itself uses `## Acceptance criteria`); reviewer must tolerate both. -->

For each R-ID in scope of this branch's diff, classify status:

| Status | Meaning |
|--------|---------|
| met | Diff clearly implements the requirement with appropriate tests |
| partial | Diff advances the requirement but leaves gaps (missing tests, missing edge case, missing integration point) |
| not-addressed | Diff does not advance this requirement at all |
| deferred | Spec explicitly defers this requirement to a later task/PR |

Report as a markdown table in the review output:

| R-ID | Status | Evidence |
|------|--------|----------|
| R1 | met | src/auth.ts:42 + tests/auth.test.ts:17 |
| R2 | partial | implementation exists but no error-path tests |
| R3 | not-addressed | — |

**Verdict gate:** any `not-addressed` R-ID (not `deferred`) → verdict must be `NEEDS_WORK`. Receipt must carry `unaddressed: ["R3"]`.
```

### epic-review/workflow.md

Same block, plus bidirectional coverage already in fn-25:

- Forward (spec → code): per-R-ID table as above
- Reverse (code → spec): for each new/modified file, trace to an R-ID or classify as `LEGITIMATE_SUPPORT` / `UNDOCUMENTED_ADDITION` / `UNRELATED_CHANGE`

Both phases feed the final verdict.

### flowctl receipt schema

In each receipt-writer (codex impl-review, codex epic-review, copilot impl-review, copilot epic-review, rp receipt writes via the skill), add optional `unaddressed` field:

```python
if unaddressed_rids:  # list of R-ID strings parsed from review output
    receipt_data["unaddressed"] = unaddressed_rids
```

Parse the `unaddressed` list from the review output by looking for a line matching `^Unaddressed R-IDs?:\s*\[([R0-9,\s]+)\]` or extracting from the table.

**Backward compatibility:** existing Ralph scripts read receipts by key; unknown/missing fields do not break anything.

### Ralph awareness (prompt-only, no script change needed)

Worker agent receives the review output and the `unaddressed` list. When fixing NEEDS_WORK, the worker prompt already says "address each issue"; with R-IDs, it gets precise targets. No Ralph script changes required — the fix loop just has better inputs.

## Rationale

MergeFoundry upstream's plan-coverage verification is one of the sharpest signals for "is this PR actually done?" Prose verdicts ("looks good") fail to catch missed requirements silently. An explicit per-R-ID table forces the reviewer to account for every criterion.

Current flow-next already has fn-25's bidirectional coverage. R-IDs make the forward direction anchor-based instead of natural-language matching.

## Acceptance

- **AC1:** impl-review workflow emits per-R-ID coverage table when spec has R-IDs.
- **AC2:** epic-review workflow emits per-R-ID coverage table (complementing fn-25's reverse coverage).
- **AC3:** Receipt writes `unaddressed: [...]` optional field when reviewer reports any `not-addressed` R-IDs.
- **AC4:** Verdict is NEEDS_WORK whenever `unaddressed` is non-empty (excluding `deferred`).
- **AC5:** Specs without R-IDs continue to work — the per-R-ID block is skipped gracefully.
- **AC6:** Existing Ralph smoke tests pass.

## Out of scope

- Strict flowctl parsing of R-ID status (reviewer LLM classifies; flowctl just stores the array).
- UI/TUI rendering of `unaddressed` (separate follow-up).
- Changing fn-25's reverse-coverage classification taxonomy.

## Dependencies

- Depends on fn-29-review-rigor-bundle.1 (R-IDs must exist in specs first).

## Done summary
Added per-R-ID requirements coverage reporting to impl-review and epic-review prompts across all three backends (rp, codex, copilot): reviewers emit a coverage table + `Unaddressed R-IDs:` summary whenever the spec uses R-IDs, flowctl parses the line (or falls back to scanning the table) into an optional `unaddressed` receipt field, and the verdict-gate instruction tells the reviewer LLM to flip NEEDS_WORK when any non-deferred R-ID is not-addressed. Backward compatible — specs without R-IDs skip the block entirely and receipts omit the field.
## Evidence
- Commits: c10d7ceea45c3635bf777697b67906d2ae820387
- Tests: plugins/flow-next/scripts/smoke_test.sh (71/71), python3 parse_unaddressed_rids unit checks (summary line + coverage table + fallbacks), python3 prompt-builder checks (build_review_prompt/build_standalone_review_prompt/build_completion_review_prompt all emit R-ID coverage block), bash shell-parser smoke (RP receipt writer handles [R3, R5] / [] / none / missing line)
- PRs: