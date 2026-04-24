# fn-29-review-rigor-bundle.1 R-IDs in epic specs + plan skill + plan-sync preservation

## Description

Add R-ID (requirement ID) convention to epic specs and propagate through plan + plan-sync. R-IDs are plain-markdown prose prefixes on acceptance criteria (`R1:`, `R2:`). Renumber-forbidden after first review cycle. Task specs gain optional `satisfies: [R1, R3]` frontmatter.

**Size:** S (prompt-only)

**Files:**
- `plugins/flow-next/skills/flow-next-plan/steps.md`
- `plugins/flow-next/skills/flow-next-plan/SKILL.md`
- `plugins/flow-next/agents/plan-sync.md`
- `CLAUDE.md` (root project guide — brief note in spec-grammar section)

## Change details

### plan/steps.md — spec template

In the epic-spec template section, update the `## Acceptance criteria` block to use R-ID prefixes. Example:

```markdown
## Acceptance criteria
- **R1:** <testable criterion>
- **R2:** <testable criterion>
- **R3:** <testable criterion>
```

Add a planning rule:

> **R-ID rule.** Number acceptance criteria as `R1`, `R2`, `R3`, ... in creation order. Once a review cycle has run against an R-ID, **never renumber**. Reordering is fine (R1, R3, R5 after R2/R4 deletion is correct). New criteria take the next unused number. Gaps are fine.

### plan/steps.md — task spec template

Add optional `satisfies: [Rn, Rm]` frontmatter to the task spec template:

```markdown
---
satisfies: [R1, R3]
---

# fn-N-slug.M Task title
```

Rule: populate only when obvious from the task description. Tasks that do infrastructure, refactoring, or shared plumbing may legitimately have no `satisfies` entry.

### plan/SKILL.md

Add one bullet under "Output rules":

- R-IDs are mandatory on new epic spec acceptance criteria (see `steps.md` R-ID rule)

### plan-sync.md agent

Add a preservation rule in the agent prompt:

> **R-ID preservation.** When syncing drift between spec and implementation:
> - Never renumber existing R-IDs.
> - New acceptance criteria take the next unused number (respect gaps).
> - If an acceptance criterion is deleted, leave the gap (do not compact).
> - When updating task specs, populate `satisfies: [...]` frontmatter if the diff clearly advances specific R-IDs.

### CLAUDE.md (root)

One sentence under the flow-next section mentioning R-ID convention and linking to the plan skill.

## Rationale

Inspired by MergeFoundry upstream's requirement-ID traceability pattern. Stable IDs survive plan edits and let review verdicts pinpoint exactly which requirements are unaddressed — not prose-matching, anchor-matching.

## Acceptance

- **AC1:** New epic specs written by plan skill have R1/R2/... prefixes on acceptance criteria.
- **AC2:** Plan skill output rules document the renumber-forbidden rule explicitly.
- **AC3:** Task specs support optional `satisfies: [Rn]` frontmatter without breaking existing parsers (frontmatter is additive).
- **AC4:** Plan-sync agent preserves existing R-IDs and populates `satisfies` where obvious.
- **AC5:** CLAUDE.md root references R-ID convention so non-flow-next readers discover it.

## Out of scope

- Retroactive R-ID injection on existing open epics (0.31+ specs stay unchanged).
- flowctl validation of R-IDs (reviewer matches them via LLM reasoning, not strict parsing).
- Enforcement of `satisfies` population (plan-sync populates when obvious; omissions are not errors).

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
