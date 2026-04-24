# fn-29-review-rigor-bundle.4 Pre-existing vs introduced classification + verdict gate

## Description

Reviewer classifies every finding as either `introduced` (caused by this branch's diff) or `pre_existing` (was broken before). Verdict only considers `introduced` findings. Pre-existing findings surface in a separate non-blocking section.

**Size:** S (prompt-only)

**Files:**
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md`
- `plugins/flow-next/skills/flow-next-epic-review/workflow.md`
- `plugins/flow-next/scripts/flowctl.py` (receipt schema — `introduced_count`, `pre_existing_count`)
- `.flow/bin/flowctl.py` (mirror)

## Change details

### Review prompts

Add a "Classification" subsection to the review prompt, above the findings format:

```markdown
## Introduced vs pre-existing classification

For each finding, determine whether it was caused by this branch's diff or was already present on the base branch.

Evidence methods (reviewer may use any):
- `git blame <file> <line>` to see when the line was last touched
- Read the base-branch version of the file directly
- Infer from diff context: if the finding is on an unchanged line in an unchanged file, it's pre_existing by default

Mark each finding:
- **introduced** — this branch caused the issue (new code, or pre-existing issue amplified/exposed by this diff in a way that now matters)
- **pre_existing** — issue was present on base branch, not caused by this branch

**Verdict gate:** only `introduced` findings affect verdict. A review with only pre-existing findings SHIPs.

Report pre-existing findings in a separate section:

## Pre-existing issues (not blocking this verdict)

- [P1, confidence 75, introduced=false] src/legacy.ts:102 — null dereference on empty array
- ...

Never delete pre-existing findings from the report — they remain visible for future work prioritization.
```

### Findings format

Classification joins severity, confidence, file, line:

```markdown
### Finding 1: [title]
- **Severity:** P1
- **Confidence:** 75
- **Classification:** introduced | pre_existing
- **Location:** src/auth.ts:42
- **Detail:** ...
- **Suggested fix:** ...
```

### flowctl receipt

Add two optional counters to receipt schema:

```python
if introduced_count is not None:
    receipt_data["introduced_count"] = introduced_count
if pre_existing_count is not None:
    receipt_data["pre_existing_count"] = pre_existing_count
```

Parse by counting classified findings in the review output. Ralph's fix loop can use `introduced_count` to confirm there's actually something to fix.

### Verdict coordination with R-IDs

Combine with fn-29-review-rigor-bundle.2 verdict gate:
- Verdict = `SHIP` only if `unaddressed` is empty AND `introduced_count` (or its P0/P1 subset) does not block
- Verdict = `NEEDS_WORK` if either gate fails
- Pre-existing findings never block

## Rationale

Reviewers without this classification tend to flag every issue in the diff neighborhood, including pre-existing problems that Ralph then spends cycles "fixing" or that block SHIP unnecessarily. MergeFoundry upstream's `pre_existing: true` separation is a clean discipline — branch responsibility stays branch-scoped.

## Acceptance

- **AC1:** Review prompts contain the introduced-vs-pre-existing classification block.
- **AC2:** Every finding in the review output carries `Classification: introduced | pre_existing`.
- **AC3:** Pre-existing findings appear in a separate "Pre-existing issues (not blocking)" section.
- **AC4:** Verdict gate treats only `introduced` findings as blocking. A diff that only surfaces pre-existing bugs verdict SHIPs.
- **AC5:** Receipt optionally carries `introduced_count` and `pre_existing_count`.
- **AC6:** Existing Ralph smoke tests pass — Ralph no longer fights pre-existing bugs.

## Out of scope

- Auto-filing pre-existing findings into a tracker (Epic 4 tracker-defer follow-up or separate epic).
- Cross-branch drift detection (comparing what's pre-existing across multiple branches).

## Done summary
Added introduced-vs-pre_existing classification to impl-review and epic-review prompts across rp/codex/copilot backends with a verdict gate that ignores pre_existing findings. Receipts optionally carry introduced_count + pre_existing_count, parsed via new parse_classification_counts() plus portable grep-based extractors in the RP workflow receipt splices.
## Evidence
- Commits: 47195bb9f9a726b955b933f909276a97d112786e
- Tests: plugins/flow-next/scripts/smoke_test.sh (69 passed, 0 failed)
- PRs: