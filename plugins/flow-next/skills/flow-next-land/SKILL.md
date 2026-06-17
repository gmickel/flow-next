---
name: flow-next-land
description: Cadence-tick autonomous babysitter for build-loop-authored PRs (/loop-shaped ship loop). Each invocation is one tick over all open PRs the build loop authored — keep CI green (bounded fix budget), wait out the reviewer patience window, resolve feedback via resolve-pr, and once converged merge + close the spec + follow the project's release instructions. Ends with a terminal LAND_VERDICT line for the driver to read. Triggers on /flow-next:land, optionally with --dry-run. Autonomous by design — never asks the user questions; reports NEEDS_HUMAN instead.
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit, Skill
---

# /flow-next:land — cadence-tick autonomous PR babysitter

A tick is one invocation of `/flow-next:land`: discover the open PRs the build loop authored, walk each through the gate tree (CI tri-state → patience window → review-thread resolution → review signal → merge gates), take at most ONE action class per PR, and end with one terminal `LAND_VERDICT` line. It is intentionally not a runner; `/loop` in Claude Code owns the cadence (babysitting waits on external events — CI, reviewers — over hours).

Land is the ship loop to pilot's build loop: pilot (`/goal`-shaped) drains ready specs into draft PRs; land (`/loop`-shaped) wakes on a cadence, acts on those PRs, sleeps. Land never authors PRs and never touches in-flight specs — it only babysits PRs whose authoring spec has ALL tasks done (the pilot-concurrency interlock).

Land and Ralph are alternative autonomous drivers. Never nest them, and never reuse Ralph harness state inside land.

**Auto-merge override (confined).** Land intentionally overrides the standing "no `gh pr merge` from skills" rule — confined to this one opt-in skill. Land itself is the gate: it merges explicitly (`--squash --delete-branch --match-head-commit`) only after every gate passes in-tick, and NEVER uses `gh pr merge --auto` (on a repo with no branch protection `--auto` merges instantly; server-side gating adds nothing). Every other skill keeps the no-auto-merge rule.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

`gh` (verified against gh 2.93.0 — re-verify `gh pr checks --json bucket`/exit-8, `--match-head-commit`, and `mergeStateStatus` on major gh bumps) and `jq` must be on PATH; `gh auth status` must pass.

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

Run these guards before discovery, ledger writes, branch changes, or skill dispatch.

```bash
if [[ -n "${FLOW_RALPH:-}" || -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  echo "Ralph and land are alternative drivers — never nest them" >&2
  echo 'LAND_VERDICT=NEEDS_HUMAN prs=0 pr=- reason="nested under Ralph harness (FLOW_RALPH/REVIEW_RECEIPT_PATH set) — refuse to run"'
  exit 1
fi

if git status --porcelain | grep -v '^.. \.flow/' >/dev/null; then
  echo 'LAND_VERDICT=NEEDS_HUMAN prs=0 pr=- reason="dirty working tree at tick start"'
  exit 0
fi
```

Dirty tree means dirty outside `.flow/`; land leaves state untouched. No cleanup, no ledger write.

## Mode Detection

Parse `$ARGUMENTS` for the dry-run switch. Unknown flags warn to stderr and are ignored. The loop avoids bash positional parameters — the host's argument interpolation rewrites positional tokens inside skill code blocks (pilot dogfood finding, 1.13.0).

```bash
RAW_ARGS="$ARGUMENTS"
LAND_DRY_RUN=0

for ARG in $RAW_ARGS; do
  case "$ARG" in
    --dry-run) LAND_DRY_RUN=1 ;;
    -*) echo "Unknown flag: $ARG (ignored by /flow-next:land)" >&2 ;;
    *)  echo "Unknown argument: $ARG (ignored by /flow-next:land)" >&2 ;;
  esac
done
export LAND_DRY_RUN
```

`--dry-run` stops after GATE: full discovery + per-PR classification report (CI tri-state read, review-signal state, would-be action) and the aggregated terminal line, with ZERO mutations — no checkout, no push, no label, no merge, no resolve-pr dispatch, no ledger write.

## The verdict contract (read this before the workflow)

Cadence drivers are transcript-blind: they read conversation output only and never run tools. Every tick therefore echoes its per-PR evidence (gate reads, action taken, verdict) into the output, one block per PR.

Per-PR verdicts are exactly: `MERGED | RELEASED | FIXING_CI | AWAITING_REVIEW | RESOLVING | BLOCKED | NEEDS_HUMAN`.

Every tick ends with exactly one terminal line, the last line of the response, with nothing after it:

```text
LAND_VERDICT=<verdict|NO_WORK> prs=<n> pr=<deciding-pr-url|-> reason="<one line>"
```

The tick-level verdict is the worst severity across PRs by priority `NEEDS_HUMAN > BLOCKED > FIXING_CI > RESOLVING > AWAITING_REVIEW > RELEASED > MERGED`; `pr=` is the URL of the PR that decided it (`-` when none). `NO_WORK` when discovery finds zero authored PRs. `prs=` is the number of PRs processed this tick.

Driver condition examples:

```text
/loop 30m /flow-next:land
/goal keep running /flow-next:land until it prints LAND_VERDICT=NO_WORK or LAND_VERDICT=NEEDS_HUMAN
```

## Forbidden

- Asking the user anything in the tick path. Land is autonomous; ambiguity maps to `NEEDS_HUMAN`.
- Authoring PRs, choosing/planning/implementing specs — that is the build loop (pilot). Land only babysits existing PRs.
- Acting on a PR without BOTH authorship signals (branch matches a spec's `branch_name` AND the make-pr breadcrumb in the PR body). Branch-only matches are reported `NEEDS_HUMAN`, never mutated.
- `gh pr merge --auto`, merge-queue enrollment, or any merge without `--match-head-commit`.
- Hand-resolving merge-conflict hunks. The conflict path is mechanical rebase only; any conflict hunk aborts → `BLOCKED`.
- Inventing release steps. Release-follow runs deterministic, non-interactive commands from the project's discovered release docs ONLY, or stops at merge.
- `git add -A` in the CI-fix path — stage only the files edited for the fix.
- Dispatching any skill other than `flow-next-resolve-pr` (with `mode:autonomous`) and `flow-next-tracker-sync` (opt-in `land.merged` touchpoint).
- Printing anything after the `LAND_VERDICT` line.
- Running under Ralph (`FLOW_RALPH` / `REVIEW_RECEIPT_PATH`).

## Workflow

Execute [workflow.md](workflow.md) in order:

1. **guards** — refuse Ralph nesting, refuse dirty non-`.flow/` start state, resolve the `.git` land ledger (read-only at this point), read `land.*` config.
2. **discover** — open specs with all tasks done → `gh pr list --head <branch_name> --state all`, OPEN-state filter, dual authorship signals, merged-but-unclosed re-entry candidates.
3. **gate** — per-PR read-only classification: durable-label skip, CI tri-state over ALL checks, patience window anchored to last push, unresolved review threads, review signal (`land.reviewSignal`), stale-approval detection, `mergeStateStatus`. `--dry-run` stops here.
   - Under the default `silence` signal, a review bot that posts a no-findings **issue comment** instead of a formal APPROVE (e.g. Codex's "Didn't find any major issues. Reviewed commit: `<sha>`") also satisfies the gate — land scans `issues/<n>/comments` for an automated-reviewer comment matching `land.cleanReviewCommentPattern` (a structured built-in default) that names the **current head SHA**. It only ever *adds* this evidence; CI, unresolved-thread, and window gates are unchanged, and a stale-SHA or non-automated comment is ignored. Set `land.cleanReviewCommentPattern` to an explicit empty string `""` to **disable** the comment path (pure reviews-API behavior); leaving it unset uses the built-in default.
4. **act** — at most one action class per PR: CI fix, resolve-pr dispatch, mechanical rebase/update, or ready→merge→post-merge tail (spec close → tracker touchpoint → release-follow).
5. **report** — per-PR verdict evidence, ledger writes, and the terminal `LAND_VERDICT` line (worst-severity rule).

## Unattended runs

Land is fully autonomous by design — there is no interactive mode. Wall-clock limits and cadence belong to the driver (`/loop <interval>`, `/goal` stop clauses). A land tick has no timeout machinery; the patience window (`land.patienceMinutes`, default 30) is gate state, not a sleep — a tick never blocks waiting for reviewers, it reports `AWAITING_REVIEW` and exits.
