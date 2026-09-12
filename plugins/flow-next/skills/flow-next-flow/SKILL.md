---
name: flow-next-flow
description: Conductor for whatever the user has - an idea or a request for a change, a spec or task id, a tracker issue, a branch or a path, a pasted bug report or console output, a how or why question about the code, something slow to speed up, a cleanup that keeps behaviour, a design fork to settle, or "what should I do next". Use when the user states any of these without naming a skill. With --auto it drives a ready spec unattended over the same route (--tick for one hop) and ends with a PILOT_VERDICT line; use when asked to auto-run or pilot a spec or the backlog.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task, Skill
---

# /flow-next:flow - the conductor

Flow chooses the next step so the user does not have to. It reads what it was given, routes from the shared routing reference, runs the routed stage skill, and continues until the next decision that belongs to a human. It re-implements no stage logic: capture, refine, plan, plan-review, work, qa, make-pr, and resolve-pr keep their own contracts, receipts, and gates. `--auto` is the same judgment behind a second entry shape: no questions, ready-flag selection instead of intent, and a terminal verdict line instead of a report; the next decision that needs a human ends the run as a verdict.

**Role:** conductor, inline (no `context: fork`) so `AskUserQuestion` stays reachable. On hosts without it, fall back to a plain-text numbered prompt with a final `Other - type your own answer` option. (sync-codex.sh rewrites the tool name for the Codex mirror.)

**Read [workflow.md](workflow.md) for the hop loop.** The routing rules live in `references/`, one file per rule, each opening with its decision record. Read a reference only at the step that names it; a step that does not name one reads nothing.

## Preamble

**CRITICAL: flowctl is BUNDLED - NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Mode detection

Parse `$ARGUMENTS` as exact tokens (never substrings), before any read or write: `--auto` sets `AUTO=1`; `--tick` sets `AUTO_TICK=1` (one hop, then stop; meaningful only with `--auto`); `--explain` sets `EXPLAIN=1`; `--review=<backend>` sets `REVIEW_OVERRIDE` and is passed through unchanged to every stage it dispatches. Everything else is the starting point, verbatim - flow adds no input classifier. A tracker issue id or URL is read through the access the session already has (the sync bridge, an MCP, `gh`, `glab`); flow adds no input adapter.

**`AUTO=1`: read [auto.md](auto.md) and follow it instead of the hop loop below.** It owns the remaining arguments (the positional spec id, `--backlog`, the research and depth passthroughs; `--explain` and `--dry-run` alike), the unattended guards and rails, selection from the ready flag, the routing-reference reads, and the terminal `PILOT_VERDICT` line. Attended runs never load it.

## Autonomy refusal - runs right after the token parse

Attended flow, `flow --auto`, and Ralph are three drivers and are never nested. Without `--auto`, flow is attended: under any autonomy marker (scan the marker namespace: `FLOW_RALPH`, `FLOW_AUTONOMOUS`, `REVIEW_RECEIPT_PATH`, `AUTONOMOUS=1`, a `mode:autonomous` token), stop before any read or write:

```
NEEDS_HUMAN: /flow-next:flow is attended - run /flow-next:flow --auto for unattended runs
```

With `--auto`, the refusal is Ralph-only (`FLOW_RALPH`, `REVIEW_RECEIPT_PATH`, in auto.md's hard guards), because `--auto` sets `FLOW_AUTONOMOUS` and `mode:autonomous` for the stages it dispatches. A run that routed, dispatched, or asked under a marker it should have refused has broken this.

## Invariants (every run)

- **Route on content and context, never on input kind.** Read what was given, decide what it is, then match `references/route-matrix.md` at the route step.
- **Ask only on a fork that is material and not observable.** Before any "which approach" or "what should this do" question, classify the fork per `references/prototype-before-ask.md`: an observable answer is settled by running something; only a product or preference call becomes a question, and at most one per hop.
- **Never fabricate a review, QA, or completion verdict** to pass a gate. Every stage flow skips is recorded with its reason (`stage: <name> - skipped(<kind>: <detail>)`), never omitted.
- **Never merge, never close the spec, never dispatch a second driver.** A run from intent ends when the PR exists; a run on an open PR converges it and stops when merge is the only step left (`references/tail.md`).
- **`--explain` writes nothing and dispatches nothing.** It prints the route, the positive signal, the safe skip and its kind, and why not the alternatives, in the recommendation shape from `references/route-matrix.md`.
- **Host command form:** print every copy-pasteable flow-next command in the spelling this host invokes - the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install), otherwise exactly as spelled here.

## Forbidden

- Running attended under any autonomy marker, or dispatching `/flow-next:land` or a second driver (`/flow-next:flow --auto`, its one-release `/flow-next:pilot` alias, Ralph) from inside a run.
- Merging, closing a spec, or force-pushing.
- Re-implementing a stage's logic inline instead of invoking its skill.
- A blocking question whose answer a prototype or experiment could have observed.
- Writing under `.flow/` on an `--explain` run.
- A stage skipped without a recorded reason.

## Report shape (every stop)

```
Flow stopped at: <the human decision, or "PR exists">
Route taken: <hop 1> -> <hop 2> -> ...   (an inline pick reads `prospect [picked: <candidate>]`)
stage: <name> - ran [<start>..<end>] | skipped(<policy|config|empty|error>: <detail>) | failed(<reason>: <detail>)   (one line per stage reached)
Next: <natural-language prompt or slash command, or the decision the user must make>
```
