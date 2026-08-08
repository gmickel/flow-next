# Overview

Tasks are written at 2.9-3.3x the fleet norm (replay agents: 6.9-7.7KB/task vs fleet p50 2.3KB, shipped 3.0KB), and the bloat is paraphrased spec context - verbatim duplication measured at ~0-1%. Root cause found in shipped prose: `skills/flow-next-plan/steps.md` tells planners that plan-time knowledge reaches executors through the task file, "no other channel" - false since fn-83, because `flowctl anchor` delivers the full parent spec verbatim alongside every task. Agents obeying that sentence copy spec context into tasks, where it is generated twice, delivered twice in every anchor, and drifts (creating exactly the work plan-sync exists to chase).

**Evidence standing: validated in the flow-efficiency replay campaign (results 06 §3, 05, toy probe 06a). No further evaluation required; the dogfood loop (implementing the waves spec with this prose) is the at-scale confirmation.** Tested wording in worktree commit `7295ac5a` (`replay/wt/flow-next-taskshape`); toy probe confirmed structure-safety at $1.38 parity cost.

## Goal & Context

Establish the artifact split as doctrine: the SPEC is the human-facing record of what and why - the artifact people pass around and review for intent. The TASK is implementation detail whose job is to be the **delegation payload**: the concrete HOW (named files, approach, ordering, task-scoped acceptance) that lets a weaker or cheaper implementer build without re-deriving design decisions. Tasks never restate spec content; they reference R-IDs and spec sections.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_review_prompt_constraints test_template_canonical -q
./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short   # idempotent
```

## Architecture & Data Models

Prose-only. Edit sites (payload `7295ac5a` verified to apply cleanly on current main):

1. `plugins/flow-next/skills/flow-next-plan/steps.md` "Task spec content" block (tested wording `7295ac5a`): artifact-split preamble (binding); corrects the false "no other channel" sentence (executors receive task + parent spec together via the anchor); never-restate rule; Description ≤10 lines; the HOW lives in Approach (replaces "What to build, not how to build it").
2. Same block, beyond the tested commit (R4): a `**Touches:**` body line beside `**Files:**` (not frontmatter - the batch create API renders frontmatter from `satisfies` only) - repo-relative paths/globs the task expects to modify, authored at plan time, checked at plan review. Authoring guidance: unknown → omit, which downstream treats as always-serial. Inert metadata to flowctl (models read it; no parsing).
3. `plugins/flow-next/skills/flow-next-plan/examples.md`: re-cut the few-shot task examples to the delegation-payload shape - calibration beats instruction (three "be brief" instructions measured ignored while few-shots size real output). Examples must show R-ID refs, concrete files/approach, `touches:` (at least once), and zero restated spec context; add one BAD example showing spec-context restatement; align the Summary table's spec/task split row.
4. `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md` (R5): the delegate prompt template already hands the executor BOTH files ("Read .flow/tasks/<task-id>.md and .flow/specs/<spec-id>.md") - so R5's check passes - but the same section still carries its own copy of the false claim ("the task file IS the brief (plan-time knowledge reaches executors through the task file, no other channel)"). Amend that parenthetical to match reality (task + parent spec together).

Mirrors: sync-codex regenerates `codex/skills/flow-next-plan/steps.md`, `codex/skills/flow-next-plan/examples.md`, `codex/skills/flow-next-work/references/codex-delegation.md`. No hash pins on any edited file. No template change (touches: lives in the plan skill's task-content scaffold, not templates/spec.md).

## Edge Cases & Constraints

- Delegation keeps working by construction: the brief template names both files; the amendment only fixes the stale sentence beside it.
- Tasks may still carry task-local Key context (surprising patterns, recent API changes) - the rule bans restatement of the spec, not task-specific knowledge.
- examples.md's existing GOOD examples are already lean - the recut sharpens them into the new shape rather than rewriting wholesale.

## Acceptance Criteria

- **R1:** The false "no other channel" claim is gone; the block states executors receive task + parent spec together. Errors: none beyond prose consistency.
- **R2:** Task-content rule block matches `7295ac5a` functionally: artifact split, never-restate, HOW mandatory, Description ≤10 lines. Errors: none.
- **R3:** examples.md few-shots show the new shape; no example restates spec context; at least one shows `touches:`. Errors: an example contradicting the rule fails review.
- **R4:** `touches:` documented in the scaffold with authoring guidance (repo-relative paths/globs; unknown → omit, which downstream treats as always-serial). Errors: none - omission is the safe default by design.
- **R5:** Delegate-brief path verified to carry the parent spec alongside the task; amended if not. Errors: a delegate receiving a lean task WITHOUT spec access is the failure this R exists to prevent. (Verified: the template reads both; the stale sentence beside it is amended.)
- **R6:** Mirrors, CHANGELOG per conventions; docs-site rides the batched release. Errors: mirror-parity red blocks merge.

## Boundaries

- No byte/length budget on tasks (rejected lever; content rules only).
- No flowctl parsing of `touches:` (models read it; deterministic tooling later only if waves needs it - not this spec).
- No anchor-bundle changes (fn-83 contract untouched).
- No retroactive rewriting of existing task files.

## Strategy Alignment

Active tracks served by this plan:
- **Self-improving through normal work** - replay findings folded into pipeline prose.
- **Cross-platform parity** - mirrors regenerated with the canonical change.

## Decision Context

The alternative - trimming the anchor to stop sending the spec - was rejected: the spec in the anchor is what makes lean tasks safe, and fn-83 proved the bundle byte-identical superset. Fixing the prose that fights the architecture is the minimal change. examples.md recut included despite being the largest edit because instruction-only changes measurably failed three times; few-shot calibration is the only sizing mechanism with evidence behind it. `touches:` placed here rather than in the waves spec because it is task-shape (what a task declares about itself); waves merely consumes it. The codex-delegation.md sentence amendment rides R1/R5 rather than a separate spec because it is the same false claim at a second site, discovered by R5's mandated check.

## Early proof point

Task fn-175.1 validates the core approach (the tested block transplants cleanly, the examples recut reads as calibration for lean delegation-payload tasks). If the recut fights the existing example structure, stop before mirrors.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | False claim gone, both-channels stated | fn-175.1 | - |
| R2  | 7295ac5a rule block | fn-175.1 | - |
| R3  | examples.md recut | fn-175.1 | - |
| R4  | touches: scaffold + guidance | fn-175.1 | - |
| R5  | Delegate brief carries spec (verified) + stale sentence amended | fn-175.1 | - |
| R6  | Mirrors + CHANGELOG | fn-175.1 (mirrors), fn-175.2 (CHANGELOG) | - |
