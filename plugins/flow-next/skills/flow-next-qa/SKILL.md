---
name: flow-next-qa
description: Live-app real-user QA pass derived from the spec. Drives the running app via flow-next-drive, derives scenarios from the spec's AC / R-IDs / boundaries, files structured P0/P1/P2 findings with evidence, and ends with a YES/NO ship verdict receipt. Consumes `.flow/features/` navigation when present. Triggers on /flow-next:qa with a spec id. Runs user-invoked OR as the optional `pipeline.qa` stage of `flow --auto` (default off). Augments — never replaces — CI/staging/manual QA. FORBIDDEN from marking PASS by reading source — the verdict rests on captured evidence from the live app, never on agent narration.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:qa — live-app real-user QA pass

Drive the running app the way an unforgiving real user would, with scenarios taken from the spec,
file P0/P1/P2 findings with captured evidence, and end with a YES/NO ship verdict written as a
`qa_verdict` receipt. The spec is the source of intent: acceptance criteria become scenarios,
R-IDs become the coverage table, boundaries say what not to test, decision context says what the
app should do.

QA is a cheap first live pass over the finished build. It does not replace CI, staging or manual
QA, and it does not fix product code: it files, surfaces and hands off. Findings are advisory; the
human reviewer and the land gate decide.

It runs when the user invokes it, or as the optional `pipeline.qa` stage (`off | on | auto`,
default `off`) that `/flow-next:flow` runs after all tasks are done and before make-pr. When
setting or reading that key, read [gate-selection.md](../flow-next-flow/references/gate-selection.md);
[`flowctl.md`](../../docs/flowctl.md) has the config row. Enable the stage only where
`/flow-next:prime` reports the app is QA-ready (seeded data, a documented dev login, a drivable
surface, readable runtime evidence); otherwise every run ends BLOCKED.

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step.

This skill runs inline on the host (not forked) so it can ask the user for undocumented facts.

## The hard rule

**SHIP rests on evidence captured from the running app** (screenshots, console output, observed
state). A SHIP reached by reading the source or the diff, from narration, or from "the code looks
right" has broken this. With no reachable app or no driver, the outcome is BLOCKED, never a pass.
Reading source to explain a failure you already captured is fine.

## Arguments

The first non-flag token is the spec id. `--target <url>`, `--receipt <path>` and `--base <ref>`
take a value (as `--flag value` or `--flag=value`). `mode:autonomous` turns on autonomous mode.

```bash
SPEC_ID=""; PREV=""
# No positional parameters: the host rewrites them inside skill code blocks.
# Quote the pasted arguments once so a URL's `&` or `;` stays data.
RAW_ARGS="$ARGUMENTS"
for ARG in $(printf '%s\n' "$RAW_ARGS"); do
  case "$PREV" in
    --target)  QA_TARGET_URL="$ARG"; PREV=""; continue ;;
    --receipt) QA_RECEIPT_OVERRIDE="$ARG"; PREV=""; continue ;;
    --base)    QA_BASE_REF="$ARG"; PREV=""; continue ;;
  esac
  case "$ARG" in
    --target|--receipt|--base) PREV="$ARG" ;;
    --target=*)  QA_TARGET_URL="${ARG#--target=}" ;;
    --receipt=*) QA_RECEIPT_OVERRIDE="${ARG#--receipt=}" ;;
    --base=*)    QA_BASE_REF="${ARG#--base=}" ;;
    mode:autonomous) QA_AUTONOMOUS=1 ;;
    -*) echo "Unknown flag: $ARG (ignored)" >&2 ;;
    *)  [[ -z "$SPEC_ID" ]] && SPEC_ID="$ARG" ;;
  esac
done
[[ -n "$PREV" ]] && echo "Flag $PREV given without a value (ignored)" >&2
[[ "${FLOW_AUTONOMOUS:-}" == "1" ]] && QA_AUTONOMOUS=1
NO_PROMPT=0
[[ "${QA_AUTONOMOUS:-}" == "1" || "${AUTONOMOUS:-}" == "1" ]] && NO_PROMPT=1
export QA_TARGET_URL QA_RECEIPT_OVERRIDE QA_BASE_REF QA_AUTONOMOUS NO_PROMPT
```

**Autonomous mode** (`NO_PROMPT=1`; `flow --auto` dispatches with `mode:autonomous`) asks
nothing. Each fact the interactive run would ask for is resolved from the spec, config or
environment; when it cannot be, the run writes a BLOCKED receipt and exits cleanly. The one
exception is an unresolvable spec id, which is an error (non-zero exit, message on stderr).

Now follow [workflow.md](workflow.md): discover, derive, prepare, execute, file, verdict.
