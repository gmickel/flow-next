# /flow-next:flow workflow - the hop loop

Mode, `EXPLAIN`, and `REVIEW_OVERRIDE` come from SKILL.md. `$FLOWCTL` is the SKILL.md preamble value.

## Preamble

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

If `.flow/` does not exist, print `No .flow/ directory - run \`$FLOWCTL init\` first.` and stop.

## Step 1: Read the starting point

Read what was given and decide what it is. Examples, never a closed list: nothing, a spec id, a task id, a tracker issue id or URL, a branch, a path, a prototype directory, a pasted bug report or console output, a sentence of intent. Read a spec or task through `$FLOWCTL show <id> --json` and `$FLOWCTL cat <id>`; a branch through `git log` and the spec whose `branch_name` matches; a tracker issue through the access this session already has; a path or prototype through the files. The result is text plus context: what exists in `.flow/` for it, what the repo shows, what the user said.

With no argument:

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

- In a fresh conversation, ask once what to work on (`plain-text numbered prompt`, or the plain-text fallback).
- In a conversation that already carries intent, ask first whether to capture that conversation into 1..n specs. A "yes" routes to `/flow-next:capture from:flow`; a "no" falls through to the fresh-conversation ask.

## Step 2: Route

Read [references/route-matrix.md](references/route-matrix.md) and match the starting state. When the match is a ready spec with no tasks and no recorded route, also read [references/plan-vs-no-plan.md](references/plan-vs-no-plan.md) and resolve the rule now; the route is recorded after the explain stop below, before any stage runs.

A spec with an intentional plan (tasks beyond the sole implicit owner) runs the planned route unchanged. A spec whose tasks are all done reads [references/gate-selection.md](references/gate-selection.md) for the QA decision and then routes to make-pr. A spec with an open PR reads [references/tail.md](references/tail.md).

When the starting point is intent that has not been captured and the criteria you would draft trip the tripwire, read [references/spec-count.md](references/spec-count.md); capture applies the same file at its own read-back, so the count is decided once.

When two routes would materially differ and the answer is not observable, read [references/prototype-before-ask.md](references/prototype-before-ask.md) before asking; ask at most one question per hop.

**`EXPLAIN=1` ends here.** Print the recommendation shape from the route matrix (route, positive signal, safe skip and its kind, why not the alternatives) and stop. No `.flow/` write, no dispatch, no route recording.

**Record the route.** Past the explain stop, when the match was a ready spec with no tasks and no recorded route, write the resolved route before anything else runs:

```bash
$FLOWCTL spec set-no-plan <spec-id> --json      # the rule resolved to direct
$FLOWCTL spec clear-no-plan <spec-id> --json    # a positive plan signal was present
```

## Step 3: Run the routed stage

Invoke the stage skill by name with its normal arguments; pass `--review=<backend>` through when `REVIEW_OVERRIDE` is set. Flow never copies a stage's steps inline. Stage-specific notes:

- **Capture under flow** is invoked with the exact token `from:flow`. Capture then applies `references/plan-vs-no-plan.md` itself, sets `no_plan` when the rule resolves to direct, and writes no placeholder requirement-coverage table on that route. The user still ratifies the draft before any write.
- **Work** runs `/flow-next:work <spec-id>`; with `no_plan` recorded the fork is pre-answered and never asks.
- **QA** runs per `references/gate-selection.md`. Under `pipeline.qa=auto`, judge drivability from the acceptance criteria and the repo before dispatching; a skip is recorded, never silent.
- **Make-pr** ends a run from intent.
- **Resolve-pr, CI fixes, re-review** converge an open PR per `references/tail.md`.

If a stage stops with `NEEDS_HUMAN`, a review verdict that needs a person, or an unresolved product question, flow stops with the same report; it never answers on the user's behalf.

## Step 4: Re-evaluate

After the stage returns, re-read state (`$FLOWCTL show <spec-id> --json`, the PR probe, the receipts) and return to Step 2. Advancement is judged on observed state, never on the stage's narration. Each hop matches the matrix afresh; there is no fixed conveyor.

## Step 5: Stop and report

Stop at the first of: the PR exists (run from intent), merge is the only step left (open-PR run), a human decision surfaced by a stage, or a plain-text numbered prompt this hop must ask. Print the report shape from SKILL.md with one `stage:` line per stage reached, then the `Next:` line in the host's command form.

Done when: every hop matched one matrix row, every dispatched or skipped stage carries a `stage:` line with its reason, no merge or spec close happened, and the report names the human decision that ended the run.
