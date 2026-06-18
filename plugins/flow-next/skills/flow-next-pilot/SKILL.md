---
name: flow-next-pilot
description: Single-tick autonomous build-loop conductor for host drivers (/loop, /goal). Each invocation advances exactly ONE ready spec by ONE pipeline stage (plan, plan-review, work, make-pr) and ends with a terminal PILOT_VERDICT line for the driver to read. Triggers on /flow-next:pilot, optionally with --spec <id>, --dry-run, --review=<backend>, --research=<grep|rp>, --depth=<level>. Autonomous by design — never asks the user questions; reports NEEDS_HUMAN instead.
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit, Skill
---

# /flow-next:pilot — single-tick autonomous build-loop conductor

A tick is one invocation of `/flow-next:pilot`: select one ready spec, classify its current stage, dispatch exactly one existing stage skill, verify state advanced, and end with one terminal `PILOT_VERDICT` line. It is intentionally not a runner; `/loop` in Claude Code or `/goal` in Claude Code / Codex owns repeated invocation.

Pilot and Ralph are alternative autonomous drivers. Ralph is an external shell loop with receipt plumbing; pilot is an in-session conductor for host loop primitives. Never nest them, and never reuse Ralph harness state inside pilot.

Human judgment lives before pilot: the spec content, `depends_on_epics`, and the fn-58 `ready` gate are the consent boundary. Pilot executes the mechanical pipeline one stage at a time, with ambiguity reported as `NEEDS_HUMAN`.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`. Subagents that run in fresh context fall back to the repo-local copy:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Pre-check: Local setup version

Non-blocking, same pattern as `/flow-next:plan` — one-line nag when the local setup lags the plugin:

```bash
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
  echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})." >&2
fi
```

Continue regardless (never blocks; silent when setup was never run or versions match).

## Hard guards (before anything else)

Run these guards before selection, ledger writes, branch changes, or skill dispatch.

```bash
if [[ -n "${FLOW_RALPH:-}" || -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  echo "Ralph and pilot are alternative drivers — never nest them" >&2
  echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="nested under Ralph harness (FLOW_RALPH/REVIEW_RECEIPT_PATH set) — refuse to run"'
  exit 1
fi

if git status --porcelain | grep -v '^.. \.flow/' >/dev/null; then
  echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="dirty working tree at tick start"'
  exit 0
fi
```

Dirty tree means dirty outside `.flow/`; pilot leaves state untouched. No cleanup, no claim reset, no strike.

## Mode Detection

Parse `$ARGUMENTS` for the scope lock, dry-run switch, and passthroughs. Unknown flags warn to stderr and are ignored. Defaults are `research=grep`, `depth=short`, and `review` resolved later via `$FLOWCTL review-backend`.

The loop handles both `--flag=value` and space-separated `--flag value` forms directly via a `PREV` token holder. It deliberately avoids bash positional parameters (`shift`-based parsing) — the host's argument interpolation rewrites positional tokens inside skill code blocks, which corrupts a `case`-on-positionals parse (observed live in the 1.13.0 dogfood).

```bash
RAW_ARGS="$ARGUMENTS"
PILOT_SPEC=""
PILOT_DRY_RUN=0
PILOT_REVIEW=""
PILOT_RESEARCH="grep"
PILOT_DEPTH="short"

PREV=""
for ARG in $RAW_ARGS; do
  case "$PREV" in
    --spec)     PILOT_SPEC="$ARG"; PREV=""; continue ;;
    --review)   PILOT_REVIEW="$ARG"; PREV=""; continue ;;
    --research) PILOT_RESEARCH="$ARG"; PREV=""; continue ;;
    --depth)    PILOT_DEPTH="$ARG"; PREV=""; continue ;;
  esac
  case "$ARG" in
    --spec|--review|--research|--depth) PREV="$ARG" ;;
    --spec=*)     PILOT_SPEC="${ARG#--spec=}" ;;
    --dry-run)    PILOT_DRY_RUN=1 ;;
    --review=*)   PILOT_REVIEW="${ARG#--review=}" ;;
    --research=*) PILOT_RESEARCH="${ARG#--research=}" ;;
    --depth=*)    PILOT_DEPTH="${ARG#--depth=}" ;;
    -*) echo "Unknown flag: $ARG (ignored by /flow-next:pilot)" >&2 ;;
    *)  echo "Unknown argument: $ARG (ignored by /flow-next:pilot)" >&2 ;;
  esac
done
[[ -n "$PREV" ]] && echo "Flag $PREV given without a value (ignored by /flow-next:pilot)" >&2
export PILOT_SPEC PILOT_DRY_RUN PILOT_REVIEW PILOT_RESEARCH PILOT_DEPTH
```

No branch flag exists in v1. Branch resolution is pilot-owned from the selected spec's `branch_name`.

## The verdict contract (read this before the workflow)

The `/goal` validator is transcript-blind: it reads conversation output only and never runs tools. Every tick therefore echoes its verification evidence into the output: flowctl status fields, task counts, task status transitions, and the gh-confirmed PR URL for make-pr.

Every tick ends with exactly one terminal line, the last line of the response, with nothing after it:

```text
PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"
```

Use `spec=-` and `stage=-` when no spec was selected. Stage values are exactly `plan`, `plan-review`, `work`, `make-pr`, `land`, or `-`.

`DEFERRED_TO_LAND` is a distinct *non-terminal-work* verdict (stage `land`): every remaining all-done candidate has an open PR that land — not pilot — owns. It is deliberately separated from `NO_WORK` so a driver can route it to `/flow-next:land` instead of stopping; an all-done spec with an open PR is real outstanding work, never absence of work.

Driver condition examples:

```text
/goal keep running /flow-next:pilot until it prints PILOT_VERDICT=NO_WORK, or stop after 20 turns
/goal keep running /flow-next:pilot --review=codex until PILOT_VERDICT=NO_WORK or PILOT_VERDICT=NEEDS_HUMAN
```

## Forbidden

- Asking the user anything in the tick path. Pilot is autonomous; ambiguity maps to `NEEDS_HUMAN`.
- Dispatching any skill outside the stage set `{plan, plan-review, work, make-pr}`. Capture, interview, QA, resolve-pr, merge, and release are never pilot stages.
- Re-implementing sub-skill logic. Pilot owns selection, dispatch, verification, verdicts, and the strikes ledger only.
- Touching gh anywhere except the all-done classification branch's PR probe and the make-pr verification probe.
- Printing anything after the `PILOT_VERDICT` line.
- Running under Ralph (`FLOW_RALPH` / `REVIEW_RECEIPT_PATH`).

## Workflow

Execute [workflow.md](workflow.md) in order:

1. **guards** — refuse Ralph nesting, refuse dirty non-`.flow/` start state, resolve the `.git` strikes ledger (read-only at this point).
2. **select** — two-pass ready-spec selection with dependency, claim, and re-bless checks.
3. **classify** — derive one stage from flowctl state; probe gh only in the all-done branch.
4. **branch** — resolve the spec branch matrix before work or make-pr.
5. **dispatch** — invoke exactly one stage skill with `mode:autonomous` plus review/research/depth passthroughs.
6. **verify** — re-read flowctl state, or gh for make-pr, and echo before/after evidence.
7. **report** — clear or record strikes, optionally unready on the second healthy no-advance tick, and print the terminal verdict.

## Unattended runs — rp caveat

The `rp` review backend runs headlessly via rp-cli — it only needs the Repo Prompt app running on the same Mac (cold start: `open -ga "Repo Prompt"`, MCP responds within seconds; a stopped app fails FAST with a clear error, never a hang). For machines without the app (remote/CI), use `--review=codex`, `--review=copilot`, or `--review=none`. Wall-clock limits and iteration caps belong to the driver (`/goal --tokens`, `/goal` stop clauses, or `/loop` cadence); a pilot tick has no timeout machinery.
