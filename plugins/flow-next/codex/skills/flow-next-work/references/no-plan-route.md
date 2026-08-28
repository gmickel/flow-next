# No-plan route (gated reference)

> **Loaded only when Phase 1's zero-task fork fires** (spec-id entry, `tasks` array empty
> in `$FLOWCTL show <spec-id> --json`). Spec-file and idea-text starts never read this
> (they mint a single task unconditionally, direct-by-construction). A spec with any
> tasks (whatever their status) never reads this file.

## Pre-answer signals (flag / natural language)

SKILL.md's option parsing records `NO_PLAN=1` from `--no-plan` or natural-language
intent ("no plan", "skip planning", "work directly"). If `NO_PLAN=1`: skip the ask, go
straight to Direct route. Contradictory signals (flag says direct, prose says plan
first) → ask instead of guessing. The flag on a spec that already has tasks was already
ignored with a one-line notice back in SKILL.md — it never reaches this file. A run
that asked under a clean `NO_PLAN=1` has broken this.

## Autonomous refusal

Under ANY autonomy marker (`FLOW_RALPH`, `FLOW_AUTONOMOUS`, `AUTONOMOUS=1` /
`mode:autonomous`, `REVIEW_RECEIPT_PATH` — scan the marker family/namespace, never a
fixed two-var list) WITHOUT an explicit no-plan instruction in the invocation, stop
with the typed report: `NEEDS_HUMAN: spec has no tasks - run /flow-next:plan <spec-id>`.
Never ask, never fall through. An explicit no-plan instruction in the dispatching
invocation is the only thing that lets an autonomous run take the Direct route — and a
contradicted signal (flag says direct, prose says plan) is never an explicit no-plan
instruction. A run that asked or continued under autonomy without that instruction has
broken this.

## The ask (interactive only)

Judge the spec (size, independent surfaces, blast-radius / riskiness of touched areas)
and state the recommendation plus its reason in one line. No static default. If the
spec is unreadable or those inputs are missing, recommend plan-first with exactly that
stated reason. Then ask and wait:

```
This spec has no tasks. How should this run proceed?
Recommend: <plan first | work directly> — <one-line reason>

a) Plan first — stop; run /flow-next:plan (reviewed task breakdown, parallelizable waves, per-task review)
b) Work directly — mint one implicit task and run the pipeline now (no task decomposition, whole spec as one unit; 3g single-task skip applies)

(Reply: "a", "b", "plan first", or just tell me)
```

A run that continued before the answer arrived has broken this.

## Plan-first answer

STOP this run with a one-line pointer: run `/flow-next:plan <spec-id>`, then re-run `/flow-next:work <spec-id>`. Work never invokes plan itself and never chains into it. A run that invoked or chained `/flow-next:plan` has broken this.

## Direct route: mint the implicit task

Refuse if the spec has no usable acceptance content (no acceptance criteria, no goal a
worker could act on): hand back to the user with a pointer to `/flow-next:plan` or
`/flow-next:interview` — never mint an empty task. Otherwise mint exactly ONE MINIMAL
task, no further confirmation:

```bash
$FLOWCTL task create --spec <spec-id> --title "Implement <spec title>" --satisfies "R1,R2,..." --json
```

`--satisfies` lists ALL the spec's R-IDs (keeps the 3g single-task policy skip and the
make-pr coverage table correct). MINIMAL body — the task never emulates plan-full by
copying a plan into the body; the agent works from the spec, the task artifact exists
for the plumbing (receipts, evidence, review dispatch, done). No `Touches:` line — a
whole-spec task genuinely cannot name its paths. Re-run after the mint resolves as the
normal resume path (task count is 1) — a second mint is unreachable by construction.
Then continue with Phase 2 (branch choice) and the standard pipeline. A run that
minted a second task, or copied a plan into the body, has broken this.

## Dispatch shape for the minted task

The standard 3c dispatch applies with these renderings. The 3a report still prints all
five report lines including `Selection rule:` — state: single minted implicit task;
the frontier is exactly one. The dispatch template's `FORBIDDEN:` field echoes declared
Touches and the minted task declares NONE, so the path ban is omitted — the field still
renders, carrying only the non-path clauses (no force-push; no rebase of the target);
the whole-spec surface is the point. `TIMEBOX:` applies unchanged. A run that printed a
path-ban `FORBIDDEN:` for this task has broken this.

## Judicious subagent use (minted-task dispatch prose)

Append the license below to the minted task's 3c dispatch prompt as extra prose.
worker.md itself gains no subagent prose, and plan-full workers get no such
license — judgment governs there (spec Decision Context, fn-209).

The worker prompt for the minted task carries a broad license: parallel implementation
of independent surfaces, background research, scouting — the SHAPE is chosen by the
harness at execution time, never prescribed here. A host without nested dispatch
degrades to serial, never errors; no capability probing. Commit ownership unchanged:
the worker is the only committer; `git add -A` and the single-commit convention stand;
hand subagents disjoint surfaces or serialize. Join barrier: every dispatched subagent
is awaited and reconciled BEFORE staging, verification, and commit — no live writer
exists at `git add -A` time (same discipline as the wave-level workspace cleanup gate
in [wave-join.md](wave-join.md)).
