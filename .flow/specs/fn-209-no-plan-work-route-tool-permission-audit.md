# No-plan work route + tool-permission audit

## Goal & Context
<!-- Goal & Context: 70% [user], 30% [paraphrase] -->

Users have requested starting `/flow-next:work` on a spec without the planning stage. Today that path is broken rather than gated: work on a zero-task spec falls through to the completion gate and can end as a "successful" run that implemented nothing, while pilot routes the same state to plan. flow-next keeps its task model and instead makes the no-plan route a first-class, recorded choice.

A second, related defect surfaced during design: the worker agent (and two other writing agents) carry a `disallowedTools: Task` ban that blocks subagent dispatch. Archaeology found no recorded rationale (the maintainer believed Task related to Claude Code's native planning feature; official docs confirm it is the subagent-dispatch tool, renamed Agent in v2.1.63). The ban's effect is narrow but real: a dispatched worker cannot spawn subagents of its own (scouts, parallel research), while conductor-level wave parallelism — multiple workers per wave — was never affected. Removing it is both a standalone fix and the enabler for the no-plan route's judicious-subagent prompt. [paraphrase]

## Architecture & Data Models
<!-- Architecture: 40% [user], 60% [paraphrase] -->

- **Work-level, not a pipeline knob.** The route lives in the work skill's spec-mode entry: a zero-task spec triggers an interactive fork (plan first vs work directly). No `pipeline.plan` config key; land is untouched, and pilot's default classification keeps routing zero tasks to plan — only an explicit `--no-plan` on the pilot invocation adds a first-match row classifying the zero-task spec to the work dispatch that carries the flag. [user]
- **One implicit task, never zero-task execution.** Once the user has chosen the direct route (ask answer, flag, or natural language), the path mints a single MINIMAL task from the spec — essentially "implement this spec" — with no further asking or confirmation. The task never emulates plan-full by copying a plan into the task body; the task artifact exists for the plumbing that needs it: receipts, evidence, review dispatch, done. The single-task completion-review policy skip composes unchanged. [user]
- **Harness-owned parallelism.** Plan-full behavior is unchanged: the plan's task decomposition and wave scheduling fix the parallelism shape up front, as today. In the plan-less fork that decision moves to execution time: the dispatch prose licenses broad judicious subagent use (implementation, research, scouting) and names no shape. [user]
- **Progressive disclosure.** The no-plan branch's machinery lives in a gated reference file loaded only when the fork fires (the established sentinel-gate pattern); plan-full runs read nothing new. [user]
- **Tool-permission model after the audit.** Writing agents (worker, pr-comment-resolver, plan-sync) lose the accidental Task denial; read-only agents (the scout family, quality-auditor, flow-gap-analyst) keep `Edit, Write, Task` because Task there closes a real escape hatch — a read-only agent that can spawn a general-purpose subagent can write through it. Confirmed at read-back. [user]
- **Mirrors follow automatically.** The codex mirror swallows `disallowedTools` and enforces via sandbox (unchanged); the OpenCode generator maps the token per-agent, so removing it removes the corresponding `task: deny` with no generator change. Cursor and Grok consume the canonical files as-is; a short parity check confirms both honor the post-audit permission model (Cursor's native readonly key; Grok's Claude-plugin compat) — the goal is parity across all hosts. [user]

## Edge Cases & Constraints
<!-- Edge Cases: 30% [user], 70% [inferred] -->

- Autonomous contexts never see the ask: a zero-task spec under Ralph/autonomous markers WITHOUT an explicit no-plan instruction stops with a typed report ("spec has no tasks — run /flow-next:plan") — never the ask, never the silent fall-through. Pilot's default classification is unchanged (zero tasks routes to plan); an explicit `--no-plan` flag on the pilot invocation classifies the zero-task spec to the work dispatch carrying the flag (a first-match row ahead of the default — otherwise the default row would consume the case and the flag could never reach work); pilot never decides no-plan on its own, and takes the flag form only (its parser has no natural-language path). [user + gap resolution]
- The plan-first answer stops the work run with a one-line pointer to /flow-next:plan; work never invokes plan itself and never chains into it. [gap resolution]
- Every subagent the judicious-dispatch prose licenses is awaited and reconciled before staging and verification — no live writer exists when the worker stages and commits. [gap resolution]
- The fork applies to the spec-id entry shape only: spec-file and idea-text starts already mint a single task unconditionally (the documented Small-task variant) and are direct-by-construction — no ask is added there. [gap resolution]
- `--no-plan` on a spec that already has tasks is ignored with a one-line notice and the planned tasks run; re-invoking after the implicit task exists resolves as the normal resume path (task count is 1), so a second mint is unreachable by construction. [gap resolution]
- Judicious subagent use never changes commit ownership: the worker remains the only committer, `git add -A` and the single-commit convention stand, and concurrent edits to one file are the worker's to serialize (prefer handing subagents disjoint surfaces). [gap resolution]
- The host-deferred review contract stays; its stated rationale moves from "worker cannot dispatch Task" (false after R1) to verdict independence — the agent that wrote the code never dispatches or issues its own review verdict. [gap resolution]
- Subagent nesting is host-dependent (Claude Code enforces a depth limit; other hosts vary): the judicious-subagent prose carries the standard portable-host degradation clause — a host without nested dispatch degrades to serial, never errors. No capability probing beyond that; harnesses improve on their own. [user]
- A spec with nothing a worker could act on refuses the direct route and hands back to the user with a pointer to plan/interview rather than minting an empty task — one line in the prose, no new ready state, deliberately not overengineered. [user]
- The legacy zero-task fall-through (a completion review over an empty diff) becomes unreachable via R2's fork; reviewers are unchanged throughout — they judge a task's diff against the spec regardless of how the task was minted. [user]

## Acceptance Criteria

Standing criteria in `.flow/criteria.md` (G-IDs) apply and are not restated. Process requirements (mirror regen twice, full gate green) ride along per the project instruction file and are not counted as R-IDs. The flow-next.dev changelog entry is an explicit post-merge hold outside this repository: the finalization task flags it in its done summary and the maintainer stages it there — it is deliberately not a task here.

- **R1:** The tool-permission audit lands as one pass: worker, pr-comment-resolver, and plan-sync stop denying Task (plan-sync keeps Write and Bash); read-only agents keep their full denial with a one-line inline rationale; the docs describing agent tool restrictions reflect the corrected understanding (Task is subagent dispatch, renamed Agent in Claude Code v2.1.63, not a planning tool); the strategy skill's Write-only allowlist gets a verdict in passing (add Edit or record it as deliberate); a short parity check confirms Cursor and Grok honor the post-audit permission model. Errors: no error surface beyond host-side nesting depth limits (degradation documented in the dispatch prose). [user]
- **R2:** `/flow-next:work <spec-id>` on a spec whose task count is zero forks explicitly instead of falling through: never-planned is distinguished from all-tasks-done, and an interactive ask offers plan-first vs work-directly with each option's consequence explained. Errors: the current fall-through (a completion review dispatched over an empty zero-task diff, or a green zero-task run) becomes unreachable; under autonomous markers with no explicit no-plan instruction the run stops with a typed "spec has no tasks" report instead of asking; reviewers themselves are unchanged — they always judge a task's diff against the spec. [user]
- **R3:** The ask's recommendation is agent-judged per spec from complexity and blast radius (spec size, independent surfaces, riskiness of touched areas), stated with its reason; no static default. Errors: judgment inputs missing (unreadable spec) falls back to recommending plan-first with that stated reason. [user]
- **R4:** A `--no-plan`-style flag and natural-language intent in the invocation ("work fn-12 no plan", "skip planning") pre-answer the fork so the ask never fires when intent is stated. Errors: contradictory signals (flag says direct, prose says plan) ask instead of guessing; the flag on a spec that already has tasks is ignored with a one-line notice. Pilot forwards an explicit `--no-plan` flag to its work dispatch: a new first-match classification row (zero tasks AND the flag present -> work, dispatched with the flag) sits ahead of the default `zero tasks -> plan` row, which is otherwise unchanged — without the flag nothing about pilot moves. [user]
- **R5:** Once the direct route is chosen, the path mints exactly one MINIMAL implicit task ("implement this spec", not an emulated plan) without further confirmation, then runs the standard work pipeline; the minted task's `satisfies` lists ALL spec R-IDs (so the 3g single-task policy skip and the make-pr coverage table stay correct) and carries no `Touches:` line (a whole-spec task genuinely cannot name its paths); receipts, review, done evidence, and the single-task completion-review policy skip compose unchanged. Errors: a spec with no usable acceptance content refuses with a pointer to plan/interview; a second mint is unreachable (task count 1 resolves as resume). [user]
- **R6:** The plan-less dispatch prose grants broad judicious subagent use — parallel implementation of independent surfaces, background research, scouting — with the shape chosen by the harness at execution time, plus the portable-host degradation clause and a join barrier: every dispatched subagent is awaited and reconciled before staging, verification, and commit. Errors: none beyond R1's documented degradation. [user]
- **R7:** The no-plan branch's machinery lives behind a gated reference loaded only when the fork fires; a plan-full run's loaded prose is unchanged. In the same pass, evaluate — defensively, no forced moves — whether existing plan-full-only machinery can also lift behind gates so neither fork always loads the other's paths. Errors: none. [user]
- **R8:** `flowctl next`'s zero-task-spec treatment is reconciled with the route: either it surfaces the state or its skip is documented as deliberate where the command is defined (the silent fall-through is code-confirmed: a zero-task spec builds empty task maps and skips the completion-review branch). Errors: none. [paraphrase]
- **R9:** The routing surfaces learn the route: a new variant in the pipeline-variations doc, the guide router can recommend it, capture's Recommended-next judgment may name it for near-zero-risk fully-known specs, and the interview write-back next-step hint includes it. Errors: none. [user]
- **R10:** work-rolling refuses a no-plan invocation with a stated reason (a single implicit task degenerates the rolling frontier) and redirects to plain work. Errors: this IS the refusal criterion. [user]

## Boundaries
<!-- Boundaries: 80% [user], 20% [paraphrase] -->

- Not for rolling workers: work-rolling keeps requiring a planned task set. [user]
- No `pipeline.plan` config key; autonomous loops keep planning by default — pilot only takes the direct route when the invocation explicitly passes a no-plan instruction through, and land is untouched. [user]
- No zero-task execution model: the task remains the unit of receipts and review. [paraphrase]
- Plan-review is not re-homed: the direct route skips the plan stage and its automatic plan-review; impl-review and completion review are unchanged, and the user can still run plan-review on the spec manually (it works on a task-less spec). [user]
- No second worker agent definition. [paraphrase]

## Quick commands

```bash
# Focused suites for the touched surfaces (full gate runs once at the end):
cd plugins/flow-next/tests && python3 -m unittest test_cursor_agent_frontmatter test_opencode_agent_frontmatter -q   # agent frontmatter (task .1)
cd plugins/flow-next/tests && python3 -m unittest test_next_zero_task -q   # flowctl next (task .4 creates this module)
./scripts/sync-codex.sh && ./scripts/sync-codex.sh   # mirror idempotency (finalization)
```

## Strategy Alignment

Active tracks served by this plan:
- **Cross-platform parity** — the tool-permission audit lands identically on Claude/Droid (frontmatter), Codex (sandbox, unchanged), OpenCode (generated permission map), and adds the Cursor/Grok parity check R1 names.

## Early proof point

Task fn-209-no-plan-work-route-tool-permission-audit.2 validates the core approach (the zero-task fork asks, the flag/NL pre-answers, and one minimal implicit task runs the standard pipeline end to end). If it fails, re-evaluate the fork-in-Phase-1 placement before continuing with the routing-surface tasks.

## Decision Context

The maintainer chose the work-level fork over a pipeline config knob ("variant 1 work-level") after seeing both laid out — the ask-plus-flag shape keeps autonomous loops planning while giving interactive users the direct route. The Task-ban removal rests on verified archaeology: the ban shipped in the worker's first commit with no rationale in commit, PR, or docs; the maintainer believed Task related to Claude Code's native planning feature; official Claude Code docs confirm Task is the subagent-dispatch tool (renamed Agent in v2.1.63, alias kept) and unrelated to plan mode or the TaskCreate checklist tools. The skill-layer allowlists were audited and found correct (skills that dispatch scouts all include Task), which narrows the fix to the three writing agents. A zero-task execution model was rejected — flow-next's receipts and reviews are keyed to tasks. The read-only agents keep their denial by explicit decision (confirmed at read-back, revising the initial "remove task everywhere"): a read-only agent that can spawn a writing subagent has an escape hatch out of read-only — the same reason Claude Code's own Explore agent excludes dispatch. The implicit task is deliberately minimal: plan-less mode must not emulate plan-full by writing a plan into the task body; the agent works from the spec, and the task artifact serves the plumbing. Planning-stage resolutions: the host-deferred review contract is kept and re-justified on verdict independence (the writer never issues its own review verdict) — the old "worker cannot dispatch Task" rationale in the work skill's prose becomes false with R1 and is corrected in the same pass. No new subagent-usage prose is added for plan-full workers — judgment governs there (deliberate; the bitter-lesson stance). work-rolling's refusal is a pre-check in its own skill file because it inherits canonical Phase 1 by pointer and would otherwise silently inherit the fork. Sequencing: fn-208 (open, in review) edits the worker agent, pilot, and interview surfaces — implementation of this spec starts from fn-208's landed state; adjacency only, no dependency edge.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Tool-permission audit pass | fn-209.1 | — |
| R2 | Zero-task fork in work | fn-209.2 | — |
| R3 | Agent-judged recommendation | fn-209.2 | — |
| R4 | Flag/NL pre-answer + pilot pass-through | fn-209.2, fn-209.3 | — |
| R5 | Minimal implicit task mint | fn-209.2 | — |
| R6 | Judicious-subagent dispatch prose | fn-209.2 | — |
| R7 | Gated reference / progressive disclosure | fn-209.2 | — |
| R8 | flowctl next reconciliation | fn-209.4 | — |
| R9 | Routing surfaces learn the route | fn-209.5 | — |
| R10 | work-rolling refusal | fn-209.5 | — |

(Task ids abbreviated: fn-209.N = fn-209-no-plan-work-route-tool-permission-audit.N. Task .6 is finalization — mirror regen, manifest, changelogs, full gate — process work with no counted R-ID.)

