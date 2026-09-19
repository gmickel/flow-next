# /flow-next:flow workflow - the hop loop

Mode, `FLOW_UNTIL`, `EXPLAIN`, and `REVIEW_OVERRIDE` come from SKILL.md. `$FLOWCTL` is the SKILL.md preamble value.

## Preamble

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

If `.flow/` does not exist, print `No .flow/ directory - run \`$FLOWCTL init\` first.` and stop.

## Step 1: Read the starting point

Read what was given and decide what it is. Examples, never a closed list: nothing, a spec id, a task id, a tracker issue id or URL, a branch, a path, a prototype directory, a pasted bug report or console output, a sentence of intent. Read a spec or task through `$FLOWCTL show <id> --json` and `$FLOWCTL cat <id>`; a branch through `git log` and the spec whose `branch_name` matches; a tracker issue through the access this session already has; a path or prototype through the files. The result is text plus context: what exists in `.flow/` for it, what the repo shows, what the user said.

With no argument, resolve the item from the most recent thing Flow can see, first match wins, then route it as if its id had been given:

1. The item this conversation last touched: the spec capture wrote, the task work closed, the PR make-pr opened. Capture's `Recommended next:` line names the step.
2. The spec whose `branch_name` matches the current branch.
3. Intent in the conversation that no spec captures yet. Ask whether to capture it into 1..n specs; a "yes" routes to `$flow-next-capture from:flow`, a "no" continues down the ladder.
4. The next open spec in `.flow`, by your judgement of readiness and order; `$FLOWCTL next` and the `ready` flag are hints. A candidate with dependencies is admitted by `$FLOWCTL spec chain <id> --json` reporting `eligible: true`, never by judgement: every dependency done, or one open **chain parent** with all tasks done and its branch on origin (work then branches from that parent's tip). An `eligible: false` candidate is skipped with the command's `reason`. Several equally plausible candidates are an inline pick, never a guess.
**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

5. Ask once what to work on (`plain-text numbered prompt`, or the plain-text fallback).

## Step 2: Route

Read [references/route-matrix.md](references/route-matrix.md). Ask once per hop, in attended and auto mode alike:

```bash
ROUTE_JSON="$("$FLOWCTL" judge --preset route --spec <spec-id> --json)"
# Intake without a live spec: state contains view=intent + intent, or
# view=brief + spec_title/spec_body, and the documented route fields.
ROUTE_JSON="$("$FLOWCTL" judge --preset route --state-file <route-state.json> --json)"
```

Use only the applicable command. `--spec` assembles fresh lifecycle state in code from the normalized spec/task inventory and `gh pr list --head <branch> --state all` (or the tracker bridge). A failed probe retains today's failure path, never a fabricated absent PR. The code resolves startable targets from documented commands, deploy URLs or the features map, trims `spec_body` at 100000 characters with `spec_body_truncated: true`, and applies first-match lifecycle order: observed PR (open, merged or closed) -> tail; all tasks done -> QA/make-pr; intentional tasks or sole implicit owner -> recorded work route; ready with zero tasks -> recorded direct or the plan-signal regex rule; not ready -> host. Existing `spec chain` admission and work's direct-owner resume admission still apply.

For intent/brief, apply `decision.value` when `decision.met`; otherwise use today's matrix judgment with only `decision.candidates` (top three probabilities), never raw Nouls as facts. `none_of_the_above` always goes to the host. Unavailable uses today's route and names `reason`. Keep the answer only for this hop: fork and auto-QA consume its answers without another request. Nouls feed the code's defect-repro/research branch and the `Signal:` line; `tiny_one_context_change` and `intent_and_boundaries_stateable` are hints only.

Print `Route: <kind> (jev <confidence>)`, `Route: <lifecycle route> (code)`, `Route: host (jev below floor: <top three>)`, or `Route: host (jev-unavailable(<reason>))` on every hop. Match the resulting route to the matrix. When the match is a ready spec with no tasks and no recorded route, also read [references/plan-vs-no-plan.md](references/plan-vs-no-plan.md) and resolve the rule now; the route is recorded after the explain stop below, before any stage runs.

A spec with an intentional plan (tasks beyond the sole implicit owner) runs the planned route unchanged. A spec whose tasks are all done reads [references/gate-selection.md](references/gate-selection.md) for the QA decision and then routes to make-pr. A spec with an existing PR, including a merged PR with unfinished tail work, reads [references/tail.md](references/tail.md).

Keep `ROUTE_JSON` inside the tool process or an ephemeral run temporary file, not tool output. Before handing a fallback to the host, run this projection with `result` parsed from that JSON; print only `host_route`. Shared QA/fork consumers read the retained full JSON directly. No durable judge state or answer log is created.

```python
# fence:judge-route-consumer
if not result["available"]:
    route_value = "host"
    host_route = {"route": "host", "line": "Route: host (jev-unavailable(%s))" % result["reason"]}
    if result.get("pr_probe_failed"):
        host_route["pr_probe_failed"] = True
else:
    decision = result["decision"]
    route_value = decision["value"] if decision["met"] else "host"
    if route_value == "host":
        candidates = decision.get("candidates", [])
        detail = ", ".join("%s %.2f" % (kind, probability) for kind, probability in candidates)
        host_route = {"route": "host", "candidates": candidates,
                      "line": "Route: host (jev below floor: %s)" % detail}
    elif "kind" in result["answers"]:
        host_route = {"route": route_value, "line": "Route: %s (jev %.2f)" % (
            route_value, result["answers"]["kind"]["confidence"])}
    else:
        host_route = {"route": route_value, "line": "Route: %s (code)" % route_value}
    if route_value != "host":
        if decision.get("research_recommended"):
            host_route["next_modifier"] = "read unfamiliar dependency documentation first"
        if "defect_repro" in decision:
            host_route["defect_repro"] = decision["defect_repro"]
```

`next_modifier` runs the research-only refine pass before work; `defect_repro=provided` runs the supplied repro, while `needed` obtains one before the fix. Neither branch predicts a verification result.

When the starting point is intent that has not been captured and the criteria you would draft trip the tripwire, read [references/spec-count.md](references/spec-count.md); capture applies the same file at its split-choice step, so the count is decided once.

When two routes would materially differ and the answer is not observable, read [references/prototype-before-ask.md](references/prototype-before-ask.md) before asking; ask at most one question per hop.

**`EXPLAIN=1` ends here.** Add `--explain` to the same `--json` judge invocation (never a second request): the structured result still feeds the projection above and the shared QA/fork consumers, and it gains an `explain` list holding the `Next:`, `Route:`, `Signal:`, `Skip/narrow:`, and `Why not the alternatives:` lines. Run the projection, then print those lines. The signal names the firing fact-grade Noul and probability; alternatives name the next two kinds and probabilities. Below-floor output names all three candidates and says the host decides. An unavailable result renders `host decides` placeholders: resolve today's route from the matrix first, then print `Next:` and `Skip/narrow:` from that route's matrix row, `Route: host (jev-unavailable(<reason>))` unchanged, and the reason as the `Signal:`. Stop. No `.flow/` write, no dispatch, no route recording.

**Record the route.** Past the explain stop, when the match was a ready spec with no tasks and no recorded route, write the resolved route before anything else runs:

```bash
$FLOWCTL spec set-no-plan <spec-id> --json      # the rule resolved to direct
$FLOWCTL spec clear-no-plan <spec-id> --json    # a positive plan signal was present
```

## Step 3: Run the routed stage

Invoke the stage skill by name with its normal arguments; pass `--review=<backend>` through when `REVIEW_OVERRIDE` is set. Flow never copies a stage's steps inline. Stage-specific notes:

- **Capture under flow** is invoked with the exact token `from:flow`. Capture then applies `references/plan-vs-no-plan.md` itself, sets `no_plan` when the rule resolves to direct, and writes no placeholder requirement-coverage table on that route. The capture request authorizes saving the spec; capture then offers the saved file for review. Honor a request to capture or review only: neither saving nor editor continuation authorizes work. A previously authorized implementation route may continue after the capture follow-up.
- **Work** runs `$flow-next-work <spec-id>`; with `no_plan` recorded the fork is pre-answered and never asks.
- **QA** runs per `references/gate-selection.md`. Under `pipeline.qa=auto`, judge drivability from the acceptance criteria and the repo before dispatching; a skip is recorded, never silent.
- **Make-pr** ends a run from intent unless the selected merge destination or current explicit scoped consent authorizes continuation.
- **Existing PR / land** follows `references/tail.md`: obtain current consent when required, bind one spec/PR, invoke one land tick, and observe its result. Explicit review-only convergence remains available without landing consent.

If a stage stops with `NEEDS_HUMAN`, a review verdict that needs a person, or an unresolved product question, flow stops with the same report; it never answers on the user's behalf.

## Step 4: Re-evaluate

After the stage returns, re-read state (`$FLOWCTL show <spec-id> --json`, the PR probe, the receipts) and return to Step 2. Advancement is judged on observed state, never on the stage's narration. Each hop matches the matrix afresh; there is no fixed conveyor.

## Step 5: Stop and report

Two kinds of human decision reach this step. A **pick among options a stage produced** (prospect's ranked candidates, a chart briefing's capture-or-split question, refine's choices when it hands back) is asked inline under the one-question-per-hop invariant, and the run continues with the answer through Step 2. A **decision that ends the run** is not askable here: a review verdict that needs a person, a `NEEDS_HUMAN` from a stage, or a product question no stage framed as options.

Apply `references/tail.md` at the PR boundary: offer landing on a plain attended existing-PR run, continue an authorized merge destination through land, and stop on decline, unanswered consent, a landing blocker, or confirmed merge plus required tail completion. Otherwise stop at the first of: the PR exists (run from intent without landing authority), a run-ending decision surfaced by a stage, or a plain-text numbered prompt this hop must ask that is not a pick. Print the report shape from SKILL.md with one `stage:` line per stage reached and each inline pick on the `Route taken` line, then the `Next:` line in the host's command form.

Done when: every hop matched one matrix row, every dispatched or skipped stage carries a `stage:` line with its reason, every inline pick is on the `Route taken` line, any merge or spec close was land-owned and currently authorized, and the report names the decision that ended the run.
