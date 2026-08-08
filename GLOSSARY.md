# Glossary

Vocabulary discipline for contributors and agents working on this repo: the words whose
synonyms cause real ambiguity, each with the aliases to avoid. Not an encyclopedia — concepts
are explained in [`plugins/flow-next/docs/README.md`](plugins/flow-next/docs/README.md); the
retired long-form text is archived at
[`agent_docs/archive/GLOSSARY-full.md`](agent_docs/archive/GLOSSARY-full.md).

## Spec

The unit of intent: `.flow/specs/<id>.md` (body) + `.flow/specs/<id>.json` (metadata sidecar). Reviewable on its own, cross-model reviewed, frozen at handover. One spec is a stream of work, not a sprint item — it holds acceptance criteria (R-IDs), not a to-do list.

_Avoid_: epic, ticket, story, PRD, requirements doc

_Relates to_: Task, R-ID, Chart

## Task

An execution unit under a spec (`fn-N.M`), sized to one `/flow-next:work` iteration (~100k tokens of fresh context). Declares `requires:` dependencies and optionally the R-IDs it `satisfies:`. Implemented by a worker subagent, never by the conductor directly.

_Avoid_: subtask, ticket, issue, story

_Relates to_: Spec, Wave

## R-ID

A numbered acceptance criterion in a spec, written `**R1:** ...`. Renumber-forbidden after the first review cycle: deletions leave gaps, new criteria take the next unused number. The load-bearing identity of a requirement across the spec, the tasks that satisfy it, the commits, and the PR coverage table. `G1`, `G2` in `.flow/criteria.md` are the same grammar lifted to project scope.

_Avoid_: AC-1, requirement #1, renumbering, req id

_Relates to_: Spec, Task

## Wave

A set of tasks whose dependencies are all satisfied at the same point — the parallel candidates `/flow-next:plan` reports. A wave is a scheduling fact derived from the dependency graph, not a time box and not a mandate to share one checkout: parallel workers get isolated workspaces and the conductor joins the wave before review.

_Avoid_: sprint, phase, batch, iteration

_Relates to_: Task

## Chart

Optional pre-capture decision mapping (`/flow-next:chart`) for one idea too large or unclear to capture in a single session: decisions (`D1`, `D2`, ...) under `.flow/charts/`, exiting as a briefing package for `/flow-next:capture`. Chart makes an effort understandable enough to plan; plan decomposes work already understood; prospect ranks plural candidate ideas. Never writes a spec, never sets `ready`.

_Avoid_: discovery doc, RFC, design doc, plan, prospect

_Relates to_: Spec, Task

## Receipt

A JSON artefact on disk that proves a step happened and gates the next one — review receipts under `.flow/review-receipts/`, green receipts under `.flow/tmp/green-receipts/`, QA verdict receipts. A receipt is a file; a verdict is the terminal line a loop skill prints into the transcript for its driver (`PILOT_VERDICT=`, `LAND_VERDICT=`). Never use one word for the other.

_Avoid_: report, log, verdict, summary

_Relates to_: Gate, Review backend

## Gate

A pass/fail check the workflow refuses to proceed past — the repo's full local quality gate (lint, typecheck, tests, docs) run before handoff, plus the review and readiness gates in the pipeline. A green receipt is the proof one exact gate command passed at one exact commit; `flowctl gate check` decides whether that proof still applies. Gates are local and fail-closed; CI is a separate surface.

_Avoid_: check, hook, CI, guardrail

_Relates to_: Receipt

## Anchor

Re-reading the spec, the task, and git state before work continues, so long sessions do not drift. `flowctl anchor <task-id>` is the per-task bundle a worker reads every iteration; `flowctl brief` is the cold-session equivalent. Not `/flow-next:prime`, which assesses whether a repo is ready for agents at all.

_Avoid_: context refresh, priming, warm-up, reload

_Relates to_: Task, Spec

## plan-sync

`/flow-next:sync` — the internal pass that updates *downstream task specs* after implementation drift, inside `.flow/`. Do not confuse it with tracker-sync (`/flow-next:tracker-sync`), which projects a spec *outward* to Linear / GitHub / GitLab / Jira and reconciles body, status, and comments. Bare "sync" is ambiguous and should not be used for either.

_Avoid_: sync, tracker-sync, resync

_Relates to_: Spec, Task

## Review backend

The engine that performs a cross-model review: `rp` (RepoPrompt), `codex`, `copilot`, `cursor`, `host`, or `none`, resolved by the `review.backend` grammar (env > per-spec/task > config). The backend is the review *mechanism*, distinct from the model it happens to run and from the reviewing agent's findings.

_Avoid_: reviewer, judge, provider, model

_Relates to_: Receipt

## Memory

Categorized durable learnings under `.flow/memory/` — `bug/<category>/` and `knowledge/<category>/` entries with YAML frontmatter, searched via `flowctl memory search`. Memory is audited, superseded, and graduated into gates; it is not a scratchpad and not a substitute for docs or code comments.

_Avoid_: notes, scratchpad, context files, learnings dump

_Relates to_: Gate

## Spine

The always-loaded body of a `SKILL.md` under branch disclosure: the universal path every run needs, with branch-only content read from `references/*.md` at the branch point. A reference is the cold-path file; the spine is the hot path. Safety nets and every-run contracts stay in the spine by rule.

_Avoid_: prompt, main file, header, preamble
