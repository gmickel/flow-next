---
name: flow-next-land
description: Autonomous PR babysitter tick. Fixes CI, resolves feedback, merges when converged, closes the spec, releases. Emits LAND_VERDICT. Use when asked to land PRs.
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit, Skill
---

# /flow-next:land — cadence-tick autonomous PR babysitter

A tick is one invocation of `/flow-next:land`: discover the open PRs the build loop authored, walk each through the gate tree (CI tri-state → patience window → review-thread resolution → review signal → merge gates), take at most ONE action class per PR, and end with one terminal `LAND_VERDICT` line. It is intentionally not a runner; `/loop` in Claude Code owns the cadence (babysitting waits on external events — CI, reviewers — over hours).

Land is the ship loop to pilot's build loop: pilot (`/goal`-shaped) drains ready specs into draft PRs; land (`/loop`-shaped) wakes on a cadence, acts on those PRs, sleeps. Land never authors PRs and never touches in-flight specs — it only babysits PRs whose authoring spec has ALL tasks done (the pilot-concurrency interlock).

Land and Ralph are alternative autonomous drivers. Never nest them, and never reuse Ralph harness state inside land.

**Auto-merge override (confined).** Land intentionally overrides the standing "no `gh pr merge` from skills" rule — confined to this one opt-in skill. Land itself is the gate: **it merges explicitly (`--squash --delete-branch --match-head-commit`) only after every gate passes in-tick, and never through `gh pr merge --auto`** (on a repo with no branch protection `--auto` merges instantly, so server-side gating adds nothing). A merge that rode `--auto`, or that landed before a gate passed, has broken this. Every other skill keeps the no-auto-merge rule.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

`gh` (verified against gh 2.93.0 — re-verify `gh pr checks --json bucket`/exit-8, `--match-head-commit`, and `mergeStateStatus` on major gh bumps) and `jq` must be on PATH; `gh auth status` must pass.

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

`--dry-run` stops after GATE: full discovery + per-PR classification report (CI tri-state read, review-signal state, would-be action) and the aggregated terminal line, **with zero mutations**. A dry-run tick that checked out, pushed, labelled, merged, dispatched resolve-pr, or wrote the ledger has broken this.

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
- Acting on a PR without both authorship signals (branch matches a spec's `branch_name` **and** the structural authorship probe — the make-pr machine marker in footer position, with the anchored dated-footer fallback for pre-marker PRs; workflow.md Phase 1). Branch-only matches are reported `NEEDS_HUMAN`, never mutated.
- `gh pr merge --auto`, merge-queue enrollment, or any merge without `--match-head-commit`.
- Hand-resolving merge-conflict hunks. The conflict path is server-side catch-up only (`gh pr update-branch`); GitHub refusing the base merge → `BLOCKED`. Land never rebases and never force-pushes.
- Inventing release steps. Release-follow runs deterministic, non-interactive commands from the project's discovered release docs, and nothing else; with no such docs it stops at merge.
- `git add -A` in the CI-fix path — stage only the files edited for the fix.
- Dispatching any skill other than `flow-next-resolve-pr` (with `mode:autonomous`) and `flow-next-tracker-sync` (opt-in `land.merged` touchpoint).
- Printing anything after the `LAND_VERDICT` line.
- Running under Ralph (`FLOW_RALPH` / `REVIEW_RECEIPT_PATH`).

## Workflow

Execute [workflow.md](workflow.md) in order:

1. **guards** — refuse Ralph nesting, refuse dirty non-`.flow/` start state, read `land.*` config, take the tick concurrency claim (non-dry ticks only; `--dry-run` takes none), then load the `.git` land ledger (read-only at this point). *Done when: both guards passed, `LAND_CFG` is captured with its fallbacks applied, and the ledger is loaded without a write — first read inside the claimed interval, never before it.*
2. **discover** — open specs with all tasks done → `gh pr list --head <branch_name> --state all`, OPEN-state filter, dual authorship signals, merged-but-unclosed re-entry candidates. *Done when: every candidate spec has a classification (babysit / re-entry / `NEEDS_HUMAN` / skipped) and the discovery table is echoed.*
3. **gate** — per-PR read-only classification: durable-label skip, CI tri-state over every check, patience window anchored to last push, unresolved review threads, review signal (`land.reviewSignal`), stale-approval detection, `mergeStateStatus`. `--dry-run` stops here. *Done when: each PR carries one planned action class plus a provisional verdict, and nothing has been mutated.*
   - Under the default `silence` signal, a review bot that posts a no-findings **issue comment** instead of a formal APPROVE also satisfies the gate — land scans `issues/<n>/comments` for an automated-reviewer comment matching `land.cleanReviewCommentPattern` (a structured built-in default) that names the **current head SHA**. The default accepts two clean shapes: the legacy clean-phrase comment (e.g. Codex's "Didn't find any major issues. Reviewed commit: `<sha>`") and Codex's edited-in-place summary-table comment whose row reads `**Code Review** | **Completed** ... <sha7>` — a summary row naming the current head is the same reviewed-this-head evidence, since findings gate separately via unresolved threads. It only ever *adds* this evidence; CI, unresolved-thread, and window gates are unchanged, and a stale-SHA or non-automated comment is ignored. Set `land.cleanReviewCommentPattern` to an explicit empty string `""` to **disable** the comment path (pure reviews-API behavior); leaving it unset uses the built-in default.
   - `land.mergeVerdictCommand` (default `""`, off) adds an opt-in **repo merge-verdict gate** (§2.9) for repos with no branch protection to gate against: once every other gate passes and the planned action is `merge`, land runs the configured command once via `bash -c` from the repo root, with context in the environment only (`FLOW_HEAD_SHA`, `FLOW_BASE_REF`, `FLOW_PR_NUMBER`, `FLOW_SPEC_ID`). Exit 0 merges; **any** non-zero - including missing, unexecutable, or timed out at the 600s bound - blocks with `NEEDS_HUMAN` and no label. It is block-only (it can never grant a merge the other gates refused), `--dry-run` reports `would-run` and executes nothing, and unset, `null`, and `""` all mean off. The command runs on the base checkout, so it must key on `$FLOW_HEAD_SHA` and refuse when it cannot see that head.
   - `land.patienceMinutesAfterReview` (default `null`, off) is a **`silence`-only refinement of the patience window** (§2.6): when the latest automated review is head-current with zero unresolved threads, the silence gate waits that many minutes measured from the review event instead of from the last push. Only the silence gate's window conjunct re-anchors — `approve`/`<login>`, the no-checks guard, the human-review-pending verdict, the stale-approval detector, and the merge call are unchanged — and a fix push reverts to the push anchor until a new head-current review exists. The report's `window=` field names the binding anchor (`anchor=<push|review>`) only when the key is configured; unset, `null`, `""`, `0`, and non-numeric values all mean off (today's push-anchored wait, byte-for-byte).
   - `land.requestReviewers` (default `""`, off) adds an opt-in **human reviewer request** (§2.6b → §3.4b): a csv of GitHub logins and/or `org/team` slugs and/or the literal `codeowners`. Exactly when a human review is the only missing merge input (CI green, zero unresolved threads, and the signal is unsatisfied under `approve`/`<login>` or satisfied-but-`REVIEW_REQUIRED` under `silence`), land plans `request-reviewers`: flips a draft PR to ready, requests the list minus the PR author (`codeowners` rides the ready flip — GitHub resolves owners itself), and records `reviewRequestSha` in the land ledger — at most once per PR per head SHA, claimed atomically so overlapping ticks cannot double-request. A failed request still records the head (no retry loop) and reports `reviewers=failed:<reason>` with the window-bounded verdict, never `BLOCKED`. It never gates a merge (`reviewSignal` does). `--dry-run` reports `reviewers=would-request` (plus `would-ready` for a draft) and mutates nothing; unset, `null`, and `""` all mean off (`reviewers=off`; when the key is set but a human review is not the sole missing input, `reviewers=skipped:not-due`).
4. **act** — at most one action class per PR: CI fix, resolve-pr dispatch, server-side catch-up (`gh pr update-branch`), human reviewer request (ready flip + `--add-reviewer`), or ready→merge→post-merge tail (spec close → release-follow → tracker touchpoint → persist-push). *Done when: each PR has had exactly one action class executed, the worktree is back on `ORIG_BRANCH` (or the merged base), and the non-`.flow/` tree is clean.*
5. **report** — per-PR verdict evidence, ledger writes, and the terminal `LAND_VERDICT` line (worst-severity rule). *Done when: one evidence block per processed PR is echoed and the terminal line is the last line of the response.*

## Unattended runs

Land is fully autonomous by design — there is no interactive mode. Wall-clock limits and cadence belong to the driver (`/loop <interval>`, `/goal` stop clauses). A land tick has no timeout machinery; the patience window (`land.patienceMinutes`, default 30) is gate state, not a sleep — a tick never blocks waiting for reviewers, it reports `AWAITING_REVIEW` and exits (`land.patienceMinutesAfterReview`, when set, only moves the `silence` gate's anchor from the last push to the head-current review event — still gate state, still no sleep).
