# Overview

Tasks are written at 2.9–3.3x the fleet norm (replay agents: 6.9–7.7KB/task vs fleet p50 2.3KB, shipped 3.0KB), and the bloat is paraphrased spec context — verbatim duplication measured at ~0–1%. Root cause found in shipped prose: `skills/flow-next-plan/steps.md` tells planners that plan-time knowledge reaches executors through the task file, "no other channel" — false since fn-83, because `flowctl anchor` delivers the full parent spec verbatim alongside every task. Agents obeying that sentence copy spec context into tasks, where it is generated twice, delivered twice in every anchor, and drifts (creating exactly the work plan-sync exists to chase).

**Evidence standing: validated in the flow-efficiency replay campaign (results 06 §3, 05, toy probe 06a). No further evaluation required; the dogfood loop (implementing the waves spec with this prose) is the at-scale confirmation.** Tested wording in worktree commit `7295ac5a` (`replay/wt/flow-next-taskshape`); toy probe confirmed structure-safety at $1.38 parity cost.

## Goal & Context

Establish the artifact split as doctrine: the SPEC is the human-facing record of what and why — the artifact people pass around and review for intent. The TASK is implementation detail whose job is to be the **delegation payload**: the concrete HOW (named files, approach, ordering, task-scoped acceptance) that lets a weaker or cheaper implementer build without re-deriving design decisions. Tasks never restate spec content; they reference R-IDs and spec sections.

## Architecture & Data Models

Prose-only. Edit sites:

1. `skills/flow-next-plan/steps.md` "Task spec content" block (tested wording `7295ac5a`): artifact-split preamble; correct the false "no other channel" sentence (executors receive task + parent spec together via the anchor); never-restate rule; Description ≤10 lines of what-this-task/why-this-split; the HOW lives in Approach.
2. Same block: replace "What to build, not how to build it" — that line predates the delegation era; the how is exactly what makes a task delegable.
3. **`skills/flow-next-plan/examples.md`: re-cut the few-shot task examples to this shape** — calibration beats instruction (measured: three "be brief" instructions ignored while few-shots size real output). Examples must show delegation-payload tasks: R-ID refs, concrete files/approach, no restated context.
4. Add a `touches:` line (paths/globs the task expects to modify) to the task-content scaffold, beside `satisfies:` — authored at plan time, checked at plan review. Consumed by the concurrent-waves spec; inert metadata to flowctl.

## Edge Cases & Constraints

- Delegation to external backends (codex `work.delegate`) must keep working: the worker composes the delegate brief FROM task + spec, so a lean task plus referenced spec loses nothing — but the work skill's delegate-brief prose must be checked to confirm it includes the parent spec, and amended in this spec if it does not.
- Tasks may still carry task-local Key context (surprising patterns, recent API changes) — the rule bans restatement of the spec, not task-specific knowledge.

## Acceptance Criteria

- **R1:** The false "no other channel" claim is gone; the block states executors receive task + parent spec together. Errors: none beyond prose consistency.
- **R2:** Task-content rule block matches `7295ac5a` functionally: artifact split, never-restate, HOW mandatory, Description ≤10 lines. Errors: none.
- **R3:** examples.md few-shots show the new shape; no example restates spec context; at least one shows `touches:`. Errors: an example contradicting the rule fails review.
- **R4:** `touches:` documented in the scaffold with authoring guidance (repo-relative paths/globs; unknown → omit, which downstream treats as always-serial). Errors: none — omission is the safe default by design.
- **R5:** Delegate-brief path verified to carry the parent spec alongside the task; amended if not. Errors: a delegate receiving a lean task WITHOUT spec access is the failure this R exists to prevent.
- **R6:** Mirrors, docs-site, CHANGELOG per conventions. Errors: mirror-parity red blocks merge.

## Boundaries

- No byte/length budget on tasks (rejected lever; content rules only).
- No flowctl parsing of `touches:` (models read it; deterministic tooling later only if waves needs it — not this spec).
- No anchor-bundle changes (fn-83 contract untouched).
- No retroactive rewriting of existing task files.

## Decision Context

The alternative — trimming the anchor to stop sending the spec — was rejected: the spec in the anchor is what makes lean tasks safe, and fn-83 proved the bundle byte-identical superset. Fixing the prose that fights the architecture is the minimal change. examples.md recut included despite being the largest edit because instruction-only changes measurably failed three times; few-shot calibration is the only sizing mechanism with evidence behind it. `touches:` placed here rather than in the waves spec because it is task-shape (what a task declares about itself); waves merely consumes it.
