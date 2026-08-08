---
satisfies: [R1, R2, R3, R4, R5]
---
# fn-175-task-shape-tasks-are-the-delegation.1 Transplant task-shape doctrine, recut examples, add touches:, amend delegate-brief sentence, regen mirrors

## Description
Land the artifact-split doctrine in the plan skill, recalibrate examples.md few-shots to the delegation-payload shape, add the touches: scaffold line, fix the second copy of the false no-other-channel claim.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan/steps.md`, `plugins/flow-next/skills/flow-next-plan/examples.md`, `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`, `plugins/flow-next/codex/**` (regenerated)

### Approach
- `git cherry-pick -n 7295ac5a` applies the steps.md payload (verified clean on main): artifact-split preamble, corrected Files line, Description rewrite.
- **touches: (R4):** in the task-content scaffold frontmatter, add `touches: [plugins/foo/src/**, docs/bar.md]` beside `satisfies:` plus a short guidance bullet under the satisfies-rules: repo-relative paths/globs the task expects to modify; authored at plan time, checked at plan review; unknown → omit (downstream treats omission as always-serial); inert to flowctl.
- **examples.md recut (R3):** sharpen the GOOD task example into the delegation-payload shape (frontmatter with satisfies + touches, Description that references the spec's R-IDs instead of restating context, HOW-forward Approach); add one BAD example showing spec-context restatement (problem framing / architecture rationale copied into a task Description) with the generated-twice/drifts problem list; align the Summary table row "What to build | How to build it" with the new doctrine (spec = what/why, task = concrete approach; full implementations stay out). Keep all other sections (investigation targets, error enumeration, proof point) untouched.
- **codex-delegation.md (R5):** the prompt-template section's parenthetical "the task file IS the brief (plan-time knowledge reaches executors through the task file, no other channel)" becomes wording that matches its own template: the executor reads the task file AND the parent spec together; the task file carries the task-specific contract. Do not touch the template itself (it already reads both files).
- `./scripts/sync-codex.sh` TWICE (second run no diff).

### Investigation targets
**Required** (read before editing):
- `git show 7295ac5a` - the payload
- `plugins/flow-next/skills/flow-next-plan/examples.md` (Good vs Bad: Task Specs + Summary table)
- `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md` ~L495-505 (prompt template section)

### Acceptance
- [ ] No "no other channel" claim anywhere in the plan skill or delegation reference; both sites state task + parent spec travel together (R1/R5)
- [ ] Rule block functionally matches 7295ac5a: artifact split, never-restate, HOW mandatory, Description limit (R2)
- [ ] examples.md: no example restates spec context; at least one shows touches:; BAD restatement example present; Summary table aligned (R3)
- [ ] touches: in scaffold with guidance incl. omit-is-safe default (R4)
- [ ] sync-codex.sh x2 idempotent; mirror diff committed
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_review_prompt_constraints test_template_canonical -q`

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
