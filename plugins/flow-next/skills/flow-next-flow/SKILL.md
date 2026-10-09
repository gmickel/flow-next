---
name: flow-next-flow
description: Conductor for whatever the user has - an idea or a request for a change, a spec or task id, a tracker issue, a branch or a path, a pasted bug report or console output, a how or why question about the code, something slow to speed up, a cleanup that keeps behaviour, a design fork to settle, or "what should I do next". Use when the user states any of these without naming a skill; --auto runs unattended.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task, Skill
---

# /flow-next:flow - the conductor

Flow chooses the next step so the user does not have to. It reads what it was given, routes from the shared routing reference, runs the routed stage skill, and continues until the next decision that belongs to a human. It re-implements no stage logic: capture, refine, plan, plan-review, work, qa, make-pr, resolve-pr, and land keep their own contracts, receipts, and gates.

**Role:** conductor, inline (no `context: fork`) so `AskUserQuestion` stays reachable. On hosts without it, fall back to a plain-text numbered prompt with a final `Other - type your own answer` option.

The hop loop is Steps 1 to 5 below. Read a reference only at the step that names it.

## Preamble

**CRITICAL: flowctl is BUNDLED - NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in the steps below) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Mode detection

Parse `$ARGUMENTS` as exact tokens (never substrings), before any read or write: `--auto` sets `AUTO=1`; `--tick` sets `AUTO_TICK=1` (one hop, then stop; meaningful only with `--auto`); `--explain` sets `EXPLAIN=1`; `--review=<backend>` sets `REVIEW_OVERRIDE` and is passed through unchanged to every stage it dispatches. The destination parse is shared by both modes:

```bash
FLOW_UNTIL=""
FLOW_DESTINATION_ERROR=0
LAND_AUTHORIZED=0
LAND_SCOPE_SPEC=""
LAND_SCOPE_PR=""
AUTO=0
for ARG in $ARGUMENTS; do
  case "$ARG" in
    --auto) AUTO=1 ;;
    --until=merge) FLOW_UNTIL=merge ;;
    --until|--until=*) FLOW_DESTINATION_ERROR=1 ;;
  esac
done
if [ "$FLOW_DESTINATION_ERROR" = 1 ]; then
  if [ "$AUTO" = 1 ]; then
    echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="invalid destination; use --until=merge"'
  else
    echo 'NEEDS_HUMAN: invalid destination; use --until=merge'
  fi
  exit 1
fi
export FLOW_UNTIL
```

`--until=merge` authorizes landing the selected item in this invocation; read `references/tail.md` at that boundary. Consent is current host context, never recovered from an environment variable, old transcript or receipt. Consume destination tokens rather than passing them to a build stage; everything else is the starting point, verbatim.

**`AUTO=1`: read [auto.md](auto.md) and follow it.** Attended runs never load it.

## Autonomy refusal - runs right after the token parse

Attended flow and `flow --auto` are two drivers and are never nested. Without `--auto`, flow is attended: under any autonomy marker (scan the marker namespace: `FLOW_AUTONOMOUS`, `AUTONOMOUS=1`, a `mode:autonomous` token), stop before any read or write:

```
NEEDS_HUMAN: /flow-next:flow is attended - run /flow-next:flow --auto for unattended runs
```

With `--auto` there is no marker refusal, because `--auto` sets `FLOW_AUTONOMOUS` and `mode:autonomous` for the stages it dispatches. A run that routed, dispatched, or asked under a marker it should have refused has broken this.

## Invariants (every run)

- **Read [working-rules.md](../../references/working-rules.md) before the first route step** and follow it on every route.
- **Route on content and context, never on input kind**, from `references/route-matrix.md` at the route step.
- **Ask only on a fork that is material and not observable** (`references/prototype-before-ask.md`); at most one question per hop.
- **Never fabricate a review, QA or completion verdict.** Every stage flow skips is recorded with its reason (`stage: <name> - skipped(<kind>: <detail>)`).
- **Invoke stage skills; never re-implement their steps inline.** Land owns merge (only with current scoped consent, per `references/tail.md`); make-pr owns spec close. Never dispatch another flow or a loop from inside a run, and never force-push.
- **`--explain` writes nothing and dispatches nothing** (`references/explain.md`).

## The hop loop

If `.flow/` does not exist, print `No .flow/ directory - run \`$FLOWCTL init\` first.` and stop.

## Step 1: Read the starting point

Read what was given and decide what it is: a spec or task id (`$FLOWCTL show <id> --json`,
`$FLOWCTL cat <id>`), a tracker issue (through the access this session already has), a branch
(`git log` and the spec whose `branch_name` matches), a path, a pasted bug report, a sentence of
intent. With no argument, read [references/no-argument.md](references/no-argument.md).

## Step 2: Route

Read [references/route-matrix.md](references/route-matrix.md). Routing and the QA gate never
ask the judge, so a run with a TypeSafe key and one without take the same route.

Then route once per hop (in auto mode, use the route `pilot snapshot` returned instead). A spec
gets the route call, which decides its lifecycle in code and never asks the judge:

```bash
"$FLOWCTL" judge --preset route --spec <spec-id> --json | jq -c '{available, reason, pr_probe_failed, decision}'
```

For a spec, code applies lifecycle order: an observed PR goes to landing, a closed spec without a
PR to you, all tasks done to QA and make-pr, a `stale` plan review to plan-review, tasks to the
recorded work route, a ready zero-task spec to direct or plan. When `decision.met` is true, use `decision.value`, unless the person asked to be interviewed on the spec or passed a refine lens with it (`--biz`, `--tech`, `--scope=<lens>`): that routes to refine (`references/plan-vs-no-plan.md`). Intake without a spec
is yours: decide from the matrix. Print one line per hop: `Route: <route> (code)` or
`Route: <route> (host)`.

`EXPLAIN=1`: resolve the route (reading the references below as needed) but record nothing, then
read [references/explain.md](references/explain.md) and stop there.

A ready spec with no tasks and no recorded route: read
[references/plan-vs-no-plan.md](references/plan-vs-no-plan.md), resolve the rule, and record it
before any stage runs (`$FLOWCTL spec set-no-plan <id> --json` for direct,
`$FLOWCTL spec clear-no-plan <id> --json` for a positive plan signal). All tasks done and no PR:
read [references/gate-selection.md](references/gate-selection.md) for QA, then make-pr. An
existing PR: read [references/tail.md](references/tail.md). Uncaptured intent whose criteria trip
the tripwire: read [references/spec-count.md](references/spec-count.md). Two routes that would
materially differ with an answer you cannot observe: read
[references/prototype-before-ask.md](references/prototype-before-ask.md) before asking, and ask at
most one question per hop.

## Step 3: Run the routed stage

Invoke the stage skill by name with its normal arguments, passing `--review=<backend>` through when
`REVIEW_OVERRIDE` is set. Never copy a stage's steps inline.

- **Capture** gets the exact token `from:flow`; it applies plan-vs-no-plan itself and offers the
  saved spec for review. A request to capture or review only never authorizes work.
- **Defect reproduction**, when the report does not say where the problem is and `.flow/features/`
  exists: read [references/defect-intake.md](references/defect-intake.md) first.
- **Work** runs `flow-next:flow-next-work <spec-id>`; a recorded `no_plan` pre-answers its fork.
  Pick the branch rather than letting work ask: `--branch=current` on a branch other than the
  default, else `--branch=new`, unless the user named one. State the choice in one line.
- **QA** follows gate-selection.md; a skip is recorded, never silent.
- **Make-pr** runs under `--auto`, or attended when the person asks for the PR (working-rules.md);
  it ends a run from intent unless `--until=merge` or current explicit consent authorizes landing
  (tail.md). A PR this run just opened gets no landing question.

A stage that stops with `NEEDS_HUMAN`, a verdict that needs a person, or an open product question
stops flow with the same report; never answer on the user's behalf.

## Step 4: Re-evaluate

Re-read state (`$FLOWCTL show <spec-id> --json`, the PR, the receipts) and return to Step 2.
Advance on observed state, never on a stage's narration.

## Step 5: Stop and report

A pick among options a stage produced (prospect's candidates, chart's capture-or-split, refine's
choices) is asked inline, one per hop, and the run continues. Otherwise stop at the first of: the PR
exists (without landing authority), a decision a stage handed to the person, or a blocking question
that is not a pick. A PR this run just opened, without landing authority, ends the run; read
tail.md at a PR boundary only otherwise. Print this report: one `stage:` line per stage reached (a
skipped stage with its reason), inline picks on the `Route taken` line, then `Next:` in the host's
command form.

```
Flow stopped at: <the human decision, "PR exists", or the observed landing outcome>
Route taken: <hop 1> -> <hop 2> -> ...   (an inline pick reads `prospect [picked: <candidate>]`)
stage: <name> - ran [<start>..<end>] | skipped(<policy|config|empty|error|reach|signal absent|despite unresolved risk>: <detail>) | failed(<reason>: <detail>)   (one line per stage reached)
Next: <natural-language prompt or slash command, or the decision the user must make>
```
