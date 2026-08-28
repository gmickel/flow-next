# No-plan work route + tool-permission audit

## Goal & Context
<!-- Goal & Context: 70% [user], 30% [paraphrase] -->

Users have requested starting `/flow-next:work` on a spec without the planning stage. Today that path is broken rather than gated: work on a zero-task spec falls through to the completion gate and can end as a "successful" run that implemented nothing, while pilot routes the same state to plan. flow-next keeps its task model and instead makes the no-plan route a first-class, recorded choice.

A second, related defect surfaced during design: the worker agent (and two other writing agents) carry a `disallowedTools: Task` ban that blocks subagent dispatch. Archaeology found no recorded rationale (the maintainer believed Task related to Claude Code's native planning feature; official docs confirm it is the subagent-dispatch tool, renamed Agent in v2.1.63). The ban's effect is narrow but real: a dispatched worker cannot spawn subagents of its own (scouts, parallel research), while conductor-level wave parallelism — multiple workers per wave — was never affected. Removing it is both a standalone fix and the enabler for the no-plan route's judicious-subagent prompt. [paraphrase]

## Architecture & Data Models
<!-- Architecture: 40% [user], 60% [paraphrase] -->

- **Work-level, not a pipeline knob.** The route lives in the work skill's spec-mode entry: a zero-task spec triggers an interactive fork (plan first vs work directly). No `pipeline.plan` config key; pilot and land are unchanged and keep routing zero tasks to plan. [user]
- **One implicit task, never zero-task execution.** Once the user has chosen the direct route (ask answer, flag, or natural language), the path mints a single MINIMAL task from the spec — essentially "implement this spec" — with no further asking or confirmation. The task never emulates plan-full by copying a plan into the task body; the task artifact exists for the plumbing that needs it: receipts, evidence, review dispatch, done. The single-task completion-review policy skip composes unchanged. [user]
- **Harness-owned parallelism.** Plan-full behavior is unchanged: the plan's task decomposition and wave scheduling fix the parallelism shape up front, as today. In the plan-less fork that decision moves to execution time: the dispatch prose licenses broad judicious subagent use (implementation, research, scouting) and names no shape. [user]
- **Progressive disclosure.** The no-plan branch's machinery lives in a gated reference file loaded only when the fork fires (the established sentinel-gate pattern); plan-full runs read nothing new. [user]
- **Tool-permission model after the audit.** Writing agents (worker, pr-comment-resolver, plan-sync) lose the accidental Task denial; read-only agents (the scout family, quality-auditor, flow-gap-analyst) keep `Edit, Write, Task` because Task there closes a real escape hatch — a read-only agent that can spawn a general-purpose subagent can write through it. Confirmed at read-back. [user]
- **Mirrors follow automatically.** The codex mirror swallows `disallowedTools` and enforces via sandbox (unchanged); the OpenCode generator maps the token per-agent, so removing it removes the corresponding `task: deny` with no generator change. Cursor and Grok consume the canonical files as-is; a short parity check confirms both honor the post-audit permission model (Cursor's native readonly key; Grok's Claude-plugin compat) — the goal is parity across all hosts. [user]

## Edge Cases & Constraints
<!-- Edge Cases: 30% [user], 70% [inferred] -->

- Autonomous contexts never see the ask: Ralph-gated work keeps current behavior, and pilot's own classification is unchanged (zero tasks routes to plan). An explicit `--no-plan` or natural-language instruction on the pilot invocation passes through to the work dispatch as the direct route — a one-line pass-through; pilot never decides no-plan on its own. [user]
- Subagent nesting is host-dependent (Claude Code enforces a depth limit; other hosts vary): the judicious-subagent prose carries the standard portable-host degradation clause — a host without nested dispatch degrades to serial, never errors. No capability probing beyond that; harnesses improve on their own. [user]
- A spec with nothing a worker could act on refuses the direct route and hands back to the user with a pointer to plan/interview rather than minting an empty task — one line in the prose, no new ready state, deliberately not overengineered. [user]
- The legacy zero-task fall-through (a completion review over an empty diff) becomes unreachable via R2's fork; reviewers are unchanged throughout — they judge a task's diff against the spec regardless of how the task was minted. [user]

## Acceptance Criteria

Standing criteria in `.flow/criteria.md` (G-IDs) apply and are not restated. Process requirements (mirror regen twice, full gate green, docs-site changelog) ride along per the project instruction file and are not counted as R-IDs.

- **R1:** The tool-permission audit lands as one pass: worker, pr-comment-resolver, and plan-sync stop denying Task (plan-sync keeps Write and Bash); read-only agents keep their full denial with a one-line inline rationale; the docs describing agent tool restrictions reflect the corrected understanding (Task is subagent dispatch, renamed Agent in Claude Code v2.1.63, not a planning tool); the strategy skill's Write-only allowlist gets a verdict in passing (add Edit or record it as deliberate); a short parity check confirms Cursor and Grok honor the post-audit permission model. Errors: no error surface beyond host-side nesting depth limits (degradation documented in the dispatch prose). [user]
- **R2:** `/flow-next:work <spec-id>` on a spec whose task count is zero forks explicitly instead of falling through: never-planned is distinguished from all-tasks-done, and an interactive ask offers plan-first vs work-directly with each option's consequence explained. Errors: the current fall-through (a completion review dispatched over an empty zero-task diff, or a green zero-task run) becomes unreachable; reviewers themselves are unchanged — they always judge a task's diff against the spec. [user]
- **R3:** The ask's recommendation is agent-judged per spec from complexity and blast radius (spec size, independent surfaces, riskiness of touched areas), stated with its reason; no static default. Errors: judgment inputs missing (unreadable spec) falls back to recommending plan-first with that stated reason. [user]
- **R4:** A `--no-plan`-style flag and natural-language intent in the invocation ("work fn-12 no plan", "skip planning") pre-answer the fork so the ask never fires when intent is stated. Errors: contradictory signals (flag says direct, prose says plan) ask instead of guessing. Pilot forwards an explicit no-plan instruction to its work dispatch unchanged (one-line pass-through; pilot's default classification stays plan). [user]
- **R5:** Once the direct route is chosen, the path mints exactly one MINIMAL implicit task ("implement this spec", not an emulated plan) without further confirmation, then runs the standard work pipeline; receipts, review, done evidence, and the single-task completion-review policy skip compose unchanged. Errors: a spec with no usable acceptance content refuses with a pointer to plan/interview. [user]
- **R6:** The plan-less dispatch prose grants broad judicious subagent use — parallel implementation of independent surfaces, background research, scouting — with the shape chosen by the harness at execution time, plus the portable-host degradation clause. Errors: none beyond R1's documented degradation. [user]
- **R7:** The no-plan branch's machinery lives behind a gated reference loaded only when the fork fires; a plan-full run's loaded prose is unchanged. In the same pass, evaluate — defensively, no forced moves — whether existing plan-full-only machinery can also lift behind gates so neither fork always loads the other's paths. Errors: none. [user]
- **R8:** `flowctl next`'s zero-task-spec treatment is reconciled with the route: either it surfaces the state or its skip is documented as deliberate where the command is defined. Errors: none. [inferred]
- **R9:** The routing surfaces learn the route: a new variant in the pipeline-variations doc, the guide router can recommend it, capture's Recommended-next judgment may name it for near-zero-risk fully-known specs, and the interview write-back next-step hint includes it. Errors: none. [user]
- **R10:** work-rolling refuses a no-plan invocation with a stated reason (a single implicit task degenerates the rolling frontier) and redirects to plain work. Errors: this IS the refusal criterion. [user]

## Boundaries
<!-- Boundaries: 80% [user], 20% [paraphrase] -->

- Not for rolling workers: work-rolling keeps requiring a planned task set. [user]
- No `pipeline.plan` config key; autonomous loops keep planning by default — pilot only takes the direct route when the invocation explicitly passes a no-plan instruction through, and land is untouched. [user]
- No zero-task execution model: the task remains the unit of receipts and review. [paraphrase]
- Plan-review is not re-homed: the direct route skips the plan stage and its automatic plan-review; impl-review and completion review are unchanged, and the user can still run plan-review on the spec manually (it works on a task-less spec). [user]
- No second worker agent definition. [paraphrase]

## Decision Context

The maintainer chose the work-level fork over a pipeline config knob ("variant 1 work-level") after seeing both laid out — the ask-plus-flag shape keeps autonomous loops planning while giving interactive users the direct route. The Task-ban removal rests on verified archaeology: the ban shipped in the worker's first commit with no rationale in commit, PR, or docs; the maintainer believed Task related to Claude Code's native planning feature; official Claude Code docs confirm Task is the subagent-dispatch tool (renamed Agent in v2.1.63, alias kept) and unrelated to plan mode or the TaskCreate checklist tools. The skill-layer allowlists were audited and found correct (skills that dispatch scouts all include Task), which narrows the fix to the three writing agents. A zero-task execution model was rejected — flow-next's receipts and reviews are keyed to tasks. The read-only agents keep their denial by explicit decision (confirmed at read-back, revising the initial "remove task everywhere"): a read-only agent that can spawn a writing subagent has an escape hatch out of read-only — the same reason Claude Code's own Explore agent excludes dispatch. The implicit task is deliberately minimal: plan-less mode must not emulate plan-full by writing a plan into the task body; the agent works from the spec, and the task artifact serves the plumbing.

## Requirement coverage

| R-ID | Task |
|------|------|
| R1–R10 | fn-N.M (TBD — populate via /flow-next:plan) |
