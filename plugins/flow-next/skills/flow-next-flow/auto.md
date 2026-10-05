# /flow-next:flow --auto - the unattended driver

Read only when SKILL.md parsed the exact `--auto` token. One run selects one ready spec and drives it through `workflow.md`'s hop (Step 2 route, Step 3 run the stage, Step 4 re-evaluate) until a terminal, or through exactly one hop under `--tick`. Every run ends with one `PILOT_VERDICT` line.

## Preamble

Reuse the `$FLOWCTL` value SKILL.md's preamble resolved.

Shared shell context for the run:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODAY="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

`jq`, `git`, and `gh` must be on PATH when classification reaches the all-done PR branch.

Cold session or run start: `$FLOWCTL brief` first for session-scope orientation (one budgeted call).

**Re-read auto.md at every run start so repeated invocations use the current instructions.**

**Check an idle dispatched agent through its commits, receipts, and status fields.** Sending it a resume message restarts it, so a merely slow agent becomes two runs.

## Hard guards (before anything else)

The first `pilot snapshot` below returns the hard guard before selection, ledger writes, branch changes, or dispatch. `guards.dirty` lists changes outside `.flow/`; a non-empty list ends `NEEDS_HUMAN`, leaves state untouched, and records no strike. The post-hop dirty guard remains in Phase 5.

## Arguments

Retain an explicit request in the current user message to review the selected spec's design before work (for example, "flow --auto fn-12; review its design first") as host context for CLASSIFY. This intent is separate from argument parsing and `--review`, which selects a backend; it expires with this run.

Parse `$ARGUMENTS` for the scope lock, the shape, the explain switch, and passthroughs. `--auto` never accepts intent, a path, a branch, or free text. The ready flag is the consent boundary and there is no capture upstream of it. The shared SKILL.md parse accepts only `--until=merge` as a destination; invalid or valueless `--until` stops before these phases. Other unknown flags warn to stderr and are ignored. Defaults are `research=grep`, `depth=short`, and `review` resolved later via `$FLOWCTL review-backend`.

Use `PREV` because host argument interpolation rewrites positional tokens inside skill code blocks.

```bash
RAW_ARGS="$ARGUMENTS"
PILOT_SPEC=""
PILOT_DRY_RUN=0              # --explain (and its one-release alias --dry-run): classify, print, stop
PILOT_REVIEW=""
PILOT_RESEARCH="grep"
PILOT_DEPTH="short"
PILOT_BACKLOG_OVERRIDE=""    # "" = use config; "1" = force backlog (--backlog)
AUTO_TICK=0                  # 1 = one hop then stop; 0 = hop until a terminal

PREV=""
for ARG in $RAW_ARGS; do
  case "$PREV" in
    --review)   PILOT_REVIEW="$ARG"; PREV=""; continue ;;
    --research) PILOT_RESEARCH="$ARG"; PREV=""; continue ;;
    --depth)    PILOT_DEPTH="$ARG"; PREV=""; continue ;;
  esac
  case "$ARG" in
    --until=merge) : ;;                         # validated by SKILL.md; not a build-stage argument
    --auto)       : ;;                         # consumed by SKILL.md mode detection
    --tick)       AUTO_TICK=1 ;;
    --review|--research|--depth) PREV="$ARG" ;;
    --explain|--dry-run) PILOT_DRY_RUN=1 ;;
    --backlog)    PILOT_BACKLOG_OVERRIDE=1 ;;
    --review=*)   PILOT_REVIEW="${ARG#--review=}" ;;
    --research=*) PILOT_RESEARCH="${ARG#--research=}" ;;
    --depth=*)    PILOT_DEPTH="${ARG#--depth=}" ;;
    -*) echo "Unknown flag: $ARG (ignored by /flow-next:flow --auto)" >&2 ;;
    *) [ -z "$PILOT_SPEC" ] && PILOT_SPEC="$ARG" || echo "Unknown argument: $ARG (ignored by /flow-next:flow --auto)" >&2 ;;
  esac
done
[[ -n "$PREV" ]] && echo "Flag $PREV given without a value (ignored by /flow-next:flow --auto)" >&2
export PILOT_SPEC PILOT_DRY_RUN PILOT_REVIEW PILOT_RESEARCH PILOT_DEPTH PILOT_BACKLOG_OVERRIDE AUTO_TICK
```

Resolve the scope and capture the hop with one read-only call. Shell variables do not survive between tool calls, so the snapshot is written to `.flow/tmp/pilot-snapshot.json` (gitignored), and every later fence that reads it starts with the same read line, which stops `NEEDS_HUMAN` when the file is missing or unparseable. An unresolved scope or snapshot error ends `NEEDS_HUMAN` with the error, never a host re-derivation or widened backlog.

```bash
SNAPSHOT_ARGS=()
[ -n "$PILOT_SPEC" ] && SNAPSHOT_ARGS+=(--spec "$PILOT_SPEC")
SNAPSHOT_FILE="$(git rev-parse --show-toplevel)/.flow/tmp/pilot-snapshot.json"
mkdir -p "$(dirname "$SNAPSHOT_FILE")" && rm -f "$SNAPSHOT_FILE" \
  || { echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="cannot reset the pilot snapshot file"'; exit 1; }
if ! PILOT_SNAPSHOT="$("$FLOWCTL" pilot snapshot "${SNAPSHOT_ARGS[@]}" --json)"; then
  printf 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="pilot snapshot failed: %s"\n' "$PILOT_SNAPSHOT"
  exit 1
fi
printf '%s' "$PILOT_SNAPSHOT" > "$SNAPSHOT_FILE" \
  || { echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="cannot write the pilot snapshot file"'; exit 1; }
[ -z "$PILOT_SPEC" ] || PILOT_SPEC="$(printf '%s' "$PILOT_SNAPSHOT" | jq -er ' .selected.id')" || exit 1
```

```bash
# fence:pilot-guards
[ -n "${PILOT_SNAPSHOT:-}" ] || PILOT_SNAPSHOT="$(cat "$(git rev-parse --show-toplevel)/.flow/tmp/pilot-snapshot.json" 2>/dev/null)"
printf '%s' "$PILOT_SNAPSHOT" | jq -e 'type == "object"' >/dev/null 2>&1 || { echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="pilot snapshot missing or unreadable; rerun the snapshot step"'; exit 1; }
if [ "$(printf '%s' "$PILOT_SNAPSHOT" | jq '.guards.dirty | length')" -gt 0 ]; then
  echo "Evidence: dirty non-.flow working tree at run start"
  printf '%s' "$PILOT_SNAPSHOT" | jq -r '.guards.dirty[]'
  echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="dirty working tree at tick start"'
  exit 0
fi
```

Apply `guards` now; never select or dispatch if the guard fails. The snapshot contains config, actor, strikes, ready candidates with chain and other-actor claims, branch-joined PR observations, selected spec/task state, review backend, route, QA freshness and before-dispatch tasks. Use those values throughout this hop. On later hops rerun the snapshot fence with `PILOT_SPEC="$SELECTED_SPEC"`, which rewrites the file, and apply the same error and guard rules.

No branch flag exists. Branch resolution is run-owned from the selected spec's `branch_name`.

There is no `--no-plan` flag. The accepted choice is the spec's `no_plan` field, set at capture, by attended flow, by work before mint, or by this run's route recording (Phase 2). A stray `--no-plan` gets the unknown-flag notice; the run never infers consent from a flag. Intentional plans and explicit design-review requests remain authoritative.

### Autonomy mode resolution - gate the wide backlog behavior

Resolve `PILOT_AUTONOMY` from `PILOT_SNAPSHOT.config.pilot.autonomy`: only the literal string `backlog` or the per-run `--backlog` override enables backlog. All other values mean `ready`. The same snapshot supplies `pipeline.qa` and `pilot.gateClasses`; no config call or TMPDIR ceremony remains.

When `PILOT_AUTONOMY=ready` (the default), the run behaves exactly as Phases 1 to 6 below describe; no backlog-mode code path runs and `references/backlog-mode.md` is not loaded. When `PILOT_AUTONOMY=backlog`, **read [references/backlog-mode.md](references/backlog-mode.md) top to bottom, execute its backlog-only setup, then continue with Phase 1**. The reference owns the backlog-only verdict extension, SELECT/TRIAGE/ASK (Phases 1.5 and 1.6), and the backlog terminals and decision log; this file keeps the autonomy export, dispatch allowlist, and never-author guards. In long-horizon mode a backlog run drives its one selected item to a terminal, then stops; the next invocation selects the next item.

## The verdict contract (read this before the phases)

The `/goal` validator is transcript-blind. It reads conversation output only and never runs tools. Every hop therefore echoes its verification evidence into the output (flowctl status fields, task counts, task status transitions, and the gh-confirmed PR URL for make-pr).

Before that line, print a `Decisions:` list: each default chosen, finding declined and review skipped on the person's behalf this run, with its evidence (working-rules.md); `Decisions: none` when there were none. The same list goes into the pull request body when make-pr runs.

Every run ends with exactly one terminal line, the last line of the response, with nothing after it. The common ready-mode grammar is:

```text
PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"
```

Use `spec=-` and `stage=-` when no spec was selected. Stage values are exactly `plan`, `plan-review`, `work`, `qa` (when the QA gate selected it), `make-pr`, `land`, or `-`. A run that dispatched more than one stage names every dispatched stage in order joined by `+` (for example `stage=work+qa+make-pr`) and carries the last hop's verdict. A `--tick` run names one stage.

`DEFERRED_TO_LAND` is a distinct *non-terminal-work* verdict (stage `land`): without current landing authority, every remaining all-done candidate has an open PR that land owns. An authorized landing tick also uses it for an observed external wait per `references/tail.md`. It is deliberately separated from `NO_WORK` so a driver can route it to `/flow-next:land` instead of stopping; an all-done spec with an open PR is real outstanding work, never absence of work.

## Forbidden

- Asking the user anything on the run path. The run is autonomous; ambiguity maps to `NEEDS_HUMAN`. `references/prototype-before-ask.md` licenses no question to the user here: an unattended fork that is not observable is `NEEDS_HUMAN` in ready mode and `ASKED` in backlog mode; an observable fork may be settled by running something only inside the dispatched stage's existing license, never by the run itself.
- Dispatching any skill outside the stage set `{plan, plan-review, work, qa, make-pr, land}`, with `qa` only when `references/gate-selection.md` selected it for this hop and `land` only through the currently authorized, scoped handoff in `references/tail.md`. Capture, refine, chart, resolve-pr, merge, and release are **never** stages of this run (capture/refine/chart are human authoring and discovery upstream of the consent boundary; resolve-pr/merge belong to land downstream of the PR; release is separate).
- Dispatching two stages in one hop. Each hop dispatches exactly one stage; the next hop re-classifies from observed state. Under `--tick`, the `make-pr` that follows a fresh QA verdict runs on the next tick.
- Re-implementing sub-skill logic. This file owns selection, classification glue, dispatch, verification, verdicts, and the strikes ledger only.
- **Never execute merge steps inline.** Without current landing authority, either mode ends at the PR (ready unless make-pr found open items). The only driver-composition exception is the scoped land stage under `references/tail.md`. Never dispatch another flow, pilot, or host loop.
- Backlog mode: see backlog-mode.md §Backlog additions to the Forbidden list.
- Touching gh anywhere except existing-PR selection, Step 2's read-only route-state PR probe, the all-done classification branch's fallback PR probe, the plan/plan-review branch row's open-PR probe, the make-pr verification probe, and the exact-target landing identity/verification reads in `references/tail.md`.
- Printing anything after the `PILOT_VERDICT` line.

## Review no-repeat terminal

When a delegated plan, implementation, or completion review exits `1` with `NOT_RETRYABLE: artifact unchanged since last verdict`, emit `PILOT_VERDICT=NEEDS_HUMAN` and end the run. It is human action (edit the artifact, explicit reset, or deliberate `--force`), never a retry/transport refund, autonomous reset/force, or redispatch. Review-counter reset and `--force` review dispatch/increment are human-only recovery tools.

## The hop loop

Run workflow.md Steps 2 to 4 with the unattended guards, branch resolution, evidence, and ledger actions in Phases 2 to 6 below. Selection (Phase 1) runs once per run and fixes the item. After Phase 6:

- `AUTO_TICK=1`: print the terminal line and stop.
- `STAGE=land`: use `references/tail.md`'s observed outcome and continuation rule, bypassing pilot strikes. Stop on confirmed merge; external waits may continue only at cadence with current consent.
- `AUTO_TICK=0` and the hop ended `ADVANCED` with a stage other than `make-pr` or `land`: append the stage to `DISPATCHED_STAGES` (joined by `+`), re-run the dirty-tree guard, rerun the snapshot fence for the same spec, and return to Phase 2 for the same spec.
- `AUTO_TICK=0` and the hop ended `ADVANCED` with `make-pr`: without landing authority, print the terminal line and stop. With `FLOW_UNTIL=merge` or current explicit scoped consent, bind the confirmed PR per `references/tail.md`, append `make-pr` to `DISPATCHED_STAGES` and re-classify this same item for land.
- Any other outcome (`NEEDS_HUMAN`, `ASKED`, `BLOCKED`, `DEFERRED_TO_LAND`, `NO_WORK`) ends the run, except the observed landing wait explicitly handled above.

The two-strike rule bounds a spec that advances nothing; the finite stage set bounds a spec that advances. A run that dies mid-way (crash, kill, session limit) leaves exactly what a dead tick leaves: committed receipts, a ledger entry, a branch. The next invocation classifies from disk; nothing is resumed from transcript.

## Phase 0.5 - Autonomy mode + backlog safety invariants

`PILOT_AUTONOMY` was resolved above (strict scalar `pilot.autonomy == "backlog"`, or the `--backlog` override). **Everything backlog-specific, the autonomy export and the safety-invariant helpers alike, lives inside a single `if [ "$PILOT_AUTONOMY" = backlog ]` branch**, so ready mode incurs zero side effects. A ready-mode run that exported `FLOW_AUTONOMOUS`, defined a helper, or loaded backlog-mode.md has broken this:

```bash
if [ "${PILOT_AUTONOMY:-ready}" != "backlog" ]; then
  : # ready mode - Phases 1-6 run exactly as written; nothing below runs;
    # FLOW_AUTONOMOUS is NOT exported; backlog-mode.md is never read.
else
  # backlog mode - everything below is scoped to THIS branch:

  # Export the autonomy marker so every sub-skill / tracker-sync op this run runs
  # unattended (AskUserQuestion is never reached). Load backlog-mode.md (the
  # agentic SELECT/TRIAGE/ASK workflow) now; Phase 1.5 / 1.6 / 3.5 execute it.
  export FLOW_AUTONOMOUS=1

  # Invariant #2 - never author a spec. The ask stage may write spec-side ONLY when
  # the spec file ALREADY exists (fill an obvious blank in an existing spec). A
  # tracker-only item has NO spec; its question parks in the tracker comment ALONE.
  # Phase 3.5 enforces this inline in its own block (shell functions do not
  # survive between tool calls).
fi
```

## Phase 1 - SELECT (two-pass)

**Ready mode only.** This two-pass selection runs when `PILOT_AUTONOMY=ready` (the default). In **backlog mode** Phase 1.5's wide SELECT replaces it entirely (it reuses the same dependency / claim / re-bless checks but widens the candidate set and acts on the skip pile instead of dropping it to `NO_WORK`). Skip directly to Phase 1.5 (backlog-mode.md) when `PILOT_AUTONOMY=backlog`.

**Existing-PR selection.** Before the open/ready build predicate, read the
named spec (or closed specs in the candidate inventory) and its exact known PR
per `references/tail.md`. A closed spec with an OPEN PR remains eligible for
landing even when no longer ready: retain it for authorized landing, or record
it as deferred without current authority. Apply this in backlog mode before
its wider SELECT as well. A named MERGED PR ends the run `NO_WORK` with its
merge commit in the reason, an already-bound one per `references/tail.md`;
missing or closed-unmerged targets stop `NEEDS_HUMAN`, never make-pr. Failed or
ambiguous probes stop safely; an unscoped run whose snapshot reports
`pr_listing_failed: true` stops `NEEDS_HUMAN`, because done specs with open
PRs are listed only from that listing. This landing path does not reopen a spec, mint
tasks, or pass it through build readiness/strike admission.

Consume `counts` and `candidates` from the snapshot in stable id order. A named scope never widens. Each candidate supplies its normalized `spec`, full `tasks`, `chain`, `other_actor_claims`, `strikes`, `would_clear_strikes`, `eligible`, branch and PR observation. `chain.eligible` is the existing dependency predicate; preserve its reason on a hold. Nonempty `other_actor_claims` holds the item. Use `actor` from the snapshot, never resolve it again.

A named scope still must pass `eligible` unless it takes the existing-PR landing path. Keep the selected row as `SPEC_JSON` / `TASKS_JSON`, `CHAIN_PARENT=chain.parent`, and `LEDGER_JSON=strikes`. A candidate with `would_clear_strikes=true` was human re-blessed: call `$FLOWCTL pilot strikes clear <id> --json` before dispatch, or report would-clear under explain. With `tracker.readyState` armed, a count of two survives board projection until the human calls `flowctl pilot strikes clear <spec-id>`. Selection does not write readiness. Existing PR candidates follow the landing consent rule above; record deferred candidates when authority is absent and continue over this same snapshot's candidates. Only `selected` carries full PR history; before classifying any other candidate (`pr.history_complete: false`), refresh with `$FLOWCTL pilot snapshot --spec <id> --json` and use its `selected` row. Never classify from an incomplete PR observation.

There are no per-candidate `show`, `tasks`, `spec chain`, actor or `gh` calls: the snapshot joins PRs by branch from one listing and shares the chain remote read. A failed PR observation is `NEEDS_HUMAN`, never absent. The host keeps consent, triage and resume-evidence judgment.

```text
PILOT_VERDICT=NO_WORK spec=- stage=- reason="no ready spec with satisfied deps"
```

Done when: exactly one candidate has passed the full predicate, or none has and the terminal above applies.

Backlog mode: Phase 1.5 SELECT and Phase 1.6 TRIAGE run from [references/backlog-mode.md](references/backlog-mode.md#phase-15---select-wide-backlog-mode-only).

## Phase 2 - CLASSIFY from the routing reference (workflow.md Step 2)

Derive dispatch flags from the snapshot. Only an explicit review option
is forwarded; the stage otherwise resolves its configured backend.

```bash
REVIEW_ARG=""
[ -n "${PILOT_SNAPSHOT:-}" ] || PILOT_SNAPSHOT="$(cat "$(git rev-parse --show-toplevel)/.flow/tmp/pilot-snapshot.json" 2>/dev/null)"
printf '%s' "$PILOT_SNAPSHOT" | jq -e 'type == "object"' >/dev/null 2>&1 || { echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="pilot snapshot missing or unreadable; rerun the snapshot step"'; exit 1; }
BACKEND_NAME="$(printf '%s' "$PILOT_SNAPSHOT" | jq -r --arg id "${SELECTED_SPEC:-}" '([.candidates[]? | select(.id == $id) | .review_backend.spec][0]) // .review_backend.spec // "ASK"')"
if [ -n "${PILOT_REVIEW:-}" ]; then
  BACKEND_NAME="$PILOT_REVIEW"
  REVIEW_ARG="--review=$PILOT_REVIEW"
fi
REVIEW_CONFIGURED=1
case "$BACKEND_NAME" in ASK|none|"") REVIEW_CONFIGURED=0 ;; esac
```

A selected review gate with `REVIEW_CONFIGURED=0` stops `NEEDS_HUMAN`.

```bash
QA_STAGE_ENABLED=0
QA_STAGE_AUTO=0
[ -n "${PILOT_SNAPSHOT:-}" ] || PILOT_SNAPSHOT="$(cat "$(git rev-parse --show-toplevel)/.flow/tmp/pilot-snapshot.json" 2>/dev/null)"
printf '%s' "$PILOT_SNAPSHOT" | jq -e 'type == "object"' >/dev/null 2>&1 || { echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="pilot snapshot missing or unreadable; rerun the snapshot step"'; exit 1; }
QA_GATE="$(printf '%s' "$PILOT_SNAPSHOT" | jq -r '.config.pipeline.qa // "off"')"
[ "${QA_GATE:-}" = "on" ] && QA_STAGE_ENABLED=1
[ "${QA_GATE:-}" = "auto" ] && QA_STAGE_AUTO=1
QA_FRESH="$(printf '%s' "$PILOT_SNAPSHOT" | jq -r --arg id "${SELECTED_SPEC:-}" '([.candidates[]? | select(.id == $id)][0] // .selected) | .qa_fresh // false')"
```

`QA_FRESH` comes from `selected.qa_fresh`. [references/gate-selection.md](references/gate-selection.md) owns the judgment. The snapshot implements [references/qa-stage.md](references/qa-stage.md)'s receipt identity, outcome and peeled branch-head checks; do not run its former shell probe.

### Route (workflow.md Step 2 runs here)

Use the selected candidate's `route` as `ROUTE_JSON` (the top-level `route` aliases the default selection) and read it as workflow Step 2 says (`decision.value` when `decision.met`, otherwise the host decides) and print its `Route:` line. The snapshot already decided the lifecycle in code; do not call judge or re-probe lifecycle fields. Routing never asks Jev, so `available` is always false here and the code decision is used with or without a key. `pr_probe_failed: true` ends `NEEDS_HUMAN` immediately. The host still applies design-review intent, [references/route-matrix.md](references/route-matrix.md), [references/gate-selection.md](references/gate-selection.md), and [references/plan-vs-no-plan.md](references/plan-vs-no-plan.md). Echo the route row and gate section.

- **Route echo.** Step 2 records the route it resolved from plan-vs-no-plan.md. Echo `route: direct - <signal absent>` or `route: plan - <the positive signal the rule named>` so a transcript-only driver sees what decided it. Under `--explain` the recording is printed as would-record and nothing is written.
- **Refusal when a selected gate needs a backend the run lacks.** A design review the reference selects (an explicit request, a `plan_review` route, or a recorded `needs_work` / `needs_human` plan review) with `REVIEW_CONFIGURED=0` is `NEEDS_HUMAN`, reason `explicit design review needs a review backend` or `unresolved plan review needs a review backend`. The run never lowers a gate.
- **Resume consent.** The spec's sole direct owner (exactly one task, `implicit_owner == true`, `no_plan == true`) is `in_progress`, its assignee matches this resolved actor (use the snapshot task and actor fields before admitting), and positive evidence proves its prior run ended (a terminal host session/process record, or an explicit user confirmation of that run's termination): `work`, resuming that owner through spec-level work, with the owner ID and the evidence reference passed as dispatch context. A claim's age, an empty ready list, missing output, or an unassigned claim is not proof; with absent or ambiguous proof keep `NEEDS_HUMAN`, never infer termination or steal a claim. `flowctl start` refuses an `in_progress` task held by this same actor unless `--reclaim` is passed; this row's evidence check is what licenses the flag, and work passes it only for the owner admitted through it - never as a driver default.
- **Blocked owners.** When every remaining non-`done` task is `blocked` or escalated, stop `NEEDS_HUMAN` with the tasks' block/escalation reasons before dispatch; record no strike. Mixed blocked and ready tasks continue on the ready tasks.
- **Stale claim.** The only non-`done` tasks are `in_progress` own/unassigned (other-actor claims were already skipped at SELECT) and no resume proof exists: `NEEDS_HUMAN`, reason `stale in-progress claim — work's ready-driven loop cannot resume it`. An own claim here may belong to a second live run of this actor on the same clone; without proof it ended, no run adds `--reclaim`.

### The all-done PR probe

Consume `selected.pr` directly (it always has `history_complete: true`): `open`, `merged`, `merged_head`, `closed`, and `probe_failed`. Set the existing `OPEN_PR`, `MERGED_PR`, `MERGED_HEAD`, `CLOSED_PR` and `PR_PROBE_FAILED` variables from those fields. `selected.branch_name`, `branch_head`, and `branch_exists` supply branch facts. No fallback PR listing is allowed.

If a PR identity was already bound by this run, bypass branch-history selection: re-read that exact PR per `references/tail.md`. Missing, mismatched or closed-unmerged targets stop; never substitute another PR. On first binding, failed/unparseable or truncated reads and multiple plausible PRs stop `NEEDS_HUMAN` before dispatch.

Apply these existing outcomes to the observed PR for `existing_pr_tail` or `all_done_make_pr` (evaluate in order, first match wins). An unfinished build still stops before land under `references/tail.md`. The all-done invariant: an all-done / completion-satisfied (`ship` or `not_required`) spec with no **merged** PR, or with merged gate PRs plus commits beyond them, is *unfinished from the board's perspective*; the run keeps driving it (`qa` or `make-pr`), defers it to land (open PR), or surfaces it (`NEEDS_HUMAN`); it never collapses to terminal `NO_WORK`:

- gh missing, unauthenticated, or API failure: `PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=make-pr reason="gh probe failed at all-done branch"`.
- OPEN PR exists: with the merge destination or current explicit scoped consent, read `references/tail.md`, bind the unique target, set `STAGE=land`, and retain this selected spec. Without that authority this spec is **deferred to land**: record it as a *deferred candidate* and skip to the next SELECT candidate. This is an explicit defer, never a silent finish: if no later candidate is selectable, the run terminates with the distinct, greppable `PILOT_VERDICT=DEFERRED_TO_LAND` line (Phase 6), never `NO_WORK`. Track the deferred spec id + open-PR url so the terminal line can name it.
- No PR exists, the spec is open, and no target was previously bound: `QA_FRESH` is the freshness input; `references/gate-selection.md` decides whether `qa` runs and `references/route-matrix.md` names what follows (a skip records the `stage: qa - skipped(config: pipeline.qa=auto: <reason>)` line in this hop's evidence). A fall-through to `NO_WORK` here has broken this. Echo `qa_gate=<off|on|auto> qa_fresh=<0|1>` in the classification report.
- MERGED PR(s) exist, spec still open, and no OPEN PR (any CLOSED PRs on the branch are irrelevant here; merged work outranks a historical closed PR, so this bullet is evaluated whenever a merged PR exists): compare `selected.branch_head` against `MERGED_HEAD` (the `headRefOid` of the merged PR with the greatest `mergedAt`, captured by the probe above). Heads differ: not an inconsistency (merged gate PRs on a reused branch with commits beyond them); classify `make-pr`, subject to the same QA gate as the no-PR bullet (this matches make-pr's Forbidden rule that closed/merged PRs on a reused branch never trigger refusal). A previously bound PR instead ends the run on its confirmed merge; it can never be replaced by a successor. Without that authority, heads equal: `NEEDS_HUMAN` (the merged branch has no new work, but the spec remains open). Empty `MERGED_HEAD` or rev-parse failure: `NEEDS_HUMAN`, unchanged. Head identity, never ancestry: land squash-merges, so a `rev-list` count against the default branch reads fully-shipped work as unshipped.
- MERGED PR exists and the spec is closed: end the run with `PILOT_VERDICT=NO_WORK spec=<id> stage=- reason="already merged: <merge commit>"`, so a driver keyed on `NO_WORK` stops.
- No PR exists and the spec is closed: `NEEDS_HUMAN`; never create a replacement.
- CLOSED PR exists, no OPEN PR, and no MERGED PR anywhere on the branch: `NEEDS_HUMAN`, because the PR was closed without merge and the run never silently reopens human-rejected work.

### Explain stop

`--explain` stops after classification. For explain, keep the snapshot route for classification and print the `Next:`, `Route:`, `Signal:`, `Skip/narrow:`, and `Why not the alternatives:` lines from its lifecycle decision as [references/explain.md](references/explain.md) says (no judge call). It also prints the selected spec, the classified stage, the routing row and gate section it came from, the review backend, task counts, consulted status fields, the resolved zero-task route as would-record (with its signal), the PR probe result if any, skipped candidates, and any would-clear ledger entries. It writes no ledger (the ledger file is never created or modified on an explain run), records no route, checks out no branch, and dispatches nothing.

```text
PILOT_VERDICT=NO_WORK spec=<id> stage=<stage> reason="dry-run: classification only, nothing dispatched"
```

Done when: exactly one stage from `{plan, plan-review, work, qa, make-pr, land}` is named, or the hop has resolved to a `NEEDS_HUMAN` / `DEFERRED_TO_LAND` terminal, with the routing row, the gate section, the consulted status fields, task counts, and any PR-probe result echoed.

## Phase 3 - Branch resolution matrix

The run owns branch resolution and runs it before every hop. Reuse `BRANCH_NAME` from Phase 2 (resolve it here when classification never reached the all-done branch):

Use `selected.branch_name` and `selected.branch_exists` from the snapshot as `BRANCH_NAME` and `BRANCH_EXISTS`.

Matrix:

| State | Action |
|---|---|
| branch exists and stage is `work` | `git checkout <branch_name>`, dispatch work with `--branch=current` |
| branch absent and stage is the first `work` hop | dispatch work with `--branch=new`; under autonomy work names it exactly the spec's `branch_name`, so later hops find it. A chained candidate (`CHAIN_PARENT` set) needs no extra row: work runs the same `spec chain` predicate and branches from `origin/<parent_branch>` itself (`flow-next-work/phases.md` Phase 2) |
| stage is `qa` and branch exists | `git checkout <branch_name>`; QA drives the running app against this branch's build (never the default branch; the app under test is the spec's build). After checkout `HEAD` equals the branch head, so the Phase 5 post-dispatch freshness verify uses `HEAD`. |
| stage is `qa` and branch absent | `NEEDS_HUMAN`, reason `all tasks done but spec branch missing — inconsistent state` (all-done with no branch is the same inconsistency as the make-pr row; QA never silently skips) |
| stage is `make-pr` and branch exists | `git checkout <branch_name>`; make-pr auto-detects the spec from the branch |
| stage is `make-pr` and branch absent | `NEEDS_HUMAN`, reason `all tasks done but spec branch missing — inconsistent state` |
| stage is `land` | Keep the bound PR and invoking checkout. Re-check current consent and pass the PR plus authorization as ordinary arguments per `references/tail.md`; no branch checkout is needed. Failure stops `NEEDS_HUMAN`, no strike. |
| stage is `plan` or `plan-review` | Use the snapshot's `current_branch_prs` and `current_branch_probe_failed` (detached HEAD is a probe failure). No open PR (including a fresh worktree branch or the default branch itself): stay on the current branch and dispatch. An open PR exists: `git checkout` the default branch (local `main`, else `master`); if that checkout fails (e.g. another worktree holds it), `NEEDS_HUMAN` naming the branch and the reason. Probe failure (gh unavailable or errors): attempt the default-branch checkout; if it fails, `NEEDS_HUMAN` (fail-safe: never plan onto a branch whose PR status is unknown). |

The invariant is that planning state is never written onto a branch with an open PR; the open-PR probe enforces it, wherever the run runs (shared checkout or secondary worktree). It guards the open-PR hazard only; a branch carrying another spec's not-yet-PR'd work is not detected. A long-horizon run may cross from a plan hop on the default branch to a work hop on the spec branch; each hop's row handles it.

If an attempted checkout fails (any attempted checkout in the matrix, including the open-PR fallback to the default branch), stop with `NEEDS_HUMAN`; do not dispatch and do not strike.

Done when: the worktree is on the branch this stage's matrix row names (or the plan/plan-review stay-put outcome applied), or the run has already terminated `NEEDS_HUMAN` without dispatching.

## Phase 4 - DISPATCH exactly one sub-skill (workflow.md Step 3)

Record the pre-dispatch evidence snapshot before invoking the stage skill:

- `plan`: task count from `before_dispatch`.
- `plan-review`: `plan_review_status` from `selected.spec`.
- `work`: per-task id/status list, spec status, and `completion_review_status`.
- `qa`: absence of a fresh `qa_verdict` receipt (`QA_FRESH=0`), already proven by the classify-time freshness probe; the post-dispatch verify re-reads the receipt against the **code head** (HEAD peeled past the qa-verdict bookkeeping commit).
- `make-pr`: no OPEN PR for the branch, already proven by the all-done probe.
- `land`: the bound spec/PR, fresh PR state and merge commit (if any), and current scope of consent per `references/tail.md`.

**Backlog mode: guard the dispatch (invariant #1).** When `PILOT_AUTONOMY=backlog`, set `DISPATCH_TARGET` to the stage's slash command and run the inline allowlist check immediately before invoking it; a forbidden or unauthorized target hard-exits `NEEDS_HUMAN` rather than dispatching:

```bash
if [ "${PILOT_AUTONOMY:-ready}" = "backlog" ]; then
  DISPATCH_TARGET="/flow-next:$STAGE"      # e.g. /flow-next:work
  case "$DISPATCH_TARGET" in
    /flow-next:plan|/flow-next:plan-review|/flow-next:work|/flow-next:qa|/flow-next:make-pr) : ;;
    /flow-next:land)
      if [ "${LAND_AUTHORIZED:-0}" != 1 ] || [ -z "${LAND_SCOPE_SPEC:-}" ] || [ -z "${LAND_SCOPE_PR:-}" ]; then
        echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=land reason="land needs current scoped authority"'
        exit 1
      fi ;;
    "/flow-next:tracker-sync reconcile"*|"/flow-next:tracker-sync question"*) : ;;
    *)
      echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="backlog mode dispatch allowlist — unauthorized stage"'
      exit 1 ;;
  esac
fi
```

Append `--review=$PILOT_REVIEW` to plan, plan-review, and work only when the user supplied it (`PILOT_REVIEW` nonempty). Never pass a resolved default or `ASK`; each stage resolves its own configured backend.

Pass `mode:autonomous` (with `FLOW_AUTONOMOUS=1` semantics for any process-level work the stage starts) and the passthroughs on each invocation:

- `plan`: `flow-next:flow-next-plan <spec-id> mode:autonomous --research=grep --depth=<level> <REVIEW_ARG-if-nonempty>`
- `plan-review`: `flow-next:flow-next-plan-review <spec-id> mode:autonomous <REVIEW_ARG-if-nonempty>`
- `work`: `flow-next:flow-next-work <spec-id> mode:autonomous --branch=<current|new> <REVIEW_ARG-if-nonempty>`; when classification took the direct route for a zero-task spec, append `--no-plan`. For an admitted direct-owner resume, append the owner ID and prior-run-ended evidence reference as dispatch context, retaining the spec target and `SPEC_MODE`.
- `qa`: `flow-next:flow-next-qa <spec-id> mode:autonomous` (the token suppresses the QA skill's prompts so the loop cannot hang on a question)
- `make-pr`: `flow-next:flow-next-make-pr <spec-id> mode:autonomous`
- `land`: `flow-next:flow-next-land` for one run, with the ordinary PR and current authorization arguments from `references/tail.md`; land's own guards and gates remain authoritative.

If a sub-skill returns `NEEDS_HUMAN` or `ESCALATE:`, stop this run with `NEEDS_HUMAN` and its reason before advancement/strike handling, even if it committed partial progress. Never re-dispatch that escalated task in this run; its persisted `in_progress` state falls under the stale-claim guard on a later run. If a sub-skill crashes, asks for judgment under autonomy, or reports ambiguity that needs a person, also stop with `NEEDS_HUMAN`. Do not cleanup, reset claims, or record a strike.

Done when: exactly one stage skill has been invoked and has returned; a hop that dispatched a second stage has broken the contract.

## Phase 5 - VERIFY + evidence echo (workflow.md Step 4)

Echo each hop's observed evidence for the transcript-only driver, decide `advanced` from the receipt and PR re-reads below, and run the post-hop dirty-tree guard. One evidence block and one stage-outcome line per hop stay in the transcript for the whole run.

**Stage-outcome line.** Every evidence echo additionally carries the one `stage:` line `references/gate-selection-more.md` (Receipts) defines for the stage this hop dispatched; a QA skip under `pipeline.qa=auto` is recorded at the classify-time skip. Append `(model: <what actually ran>)` only when this hop knows what executed the stage (a named subagent model, a bridged CLI invoked with an explicit model, a review backend that reported one). Record what ran, never what the routing block preferred, and omit the annotation when the harness did not expose it rather than writing `auto` / `default` / `unknown`. Timestamps only where this hop knows them; token/cost telemetry is out of scope (host-side data flowctl cannot observe).

For `land`, execute `references/tail.md`'s fresh observations and outcome mapping. Pass through the original land result and its per-PR evidence; do not apply the build-stage advancement/strike rules to a landing wait or blocker.

For `plan`, advancement means tasks now exist:

```text
Evidence:
stage=plan
task_count.before=<n>
task_count.after=<m>
advanced=<m > 0>
```

For `plan-review`, advancement means the field is now `ship`:

```text
Evidence:
stage=plan-review
plan_review_status.before=<value>
plan_review_status.after=<value>
advanced=<after == ship>
```

For `work`, advancement means at least one task/spec status transition occurred, or `completion_review_status` newly entered the satisfying set (`ship`, or the policy-excused `not_required`) when that gate was the work to do; `not_required` counts as advanced, since logging it as a no-advance would burn a false strike:

```text
Evidence:
stage=work
tasks.before=<id:status,...>
tasks.after=<id:status,...>
spec_status.before=<value>
spec_status.after=<value>
completion_review_status.before=<value>
completion_review_status.after=<value>
advanced=<true|false>
```

When the work stage's output contains a `Sequential fallback:` line, repeat that line verbatim in the evidence echo.

For `qa`, advancement is judged from the **post-dispatch `qa_verdict` receipt**, observed state, never the QA skill's narration. Read the receipt's `qa_outcome` field, never the `verdict` projection (the QA skill projects `BLOCKED->verdict=NEEDS_WORK`, so a hop that read `verdict` conflated "couldn't verify" with "found problems" and has broken this).

Read the receipt fresh after dispatch. The QA skill commits its own handoff in autonomous mode (qa §6.3b), so `HEAD` is now the `chore(flow): qa verdict` commit; peel it to the **code head** and match the receipt's `head_sha` against that (the pr-artifact commit can't exist yet; that is the next hop's make-pr):

```bash
QA_RECEIPT="$REPO_ROOT/.flow/review-receipts/qa-$SELECTED_SPEC.json"
QA_OUTCOME=""
QA_ADVANCED=false
# Code head = HEAD, peeled past qa's own `chore(flow): qa verdict` handoff commit (§6.3b).
CODE_HEAD="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "")"
git -C "$REPO_ROOT" log -1 --format='%s' 2>/dev/null | grep -q '^chore(flow): qa verdict ' \
  && CODE_HEAD="$(git -C "$REPO_ROOT" rev-parse HEAD^ 2>/dev/null || echo "")"
if [ -f "$QA_RECEIPT" ]; then
  QA_OUTCOME="$(jq -r '.qa_outcome // ""' "$QA_RECEIPT" 2>/dev/null || echo "")"
  # Advance ONLY on a FRESH receipt this dispatch produced: id matches, head_sha == the code
  # head, terminal outcome. A missing/stale receipt (qa errored before writing) =>
  # advanced=false; never advance on narration.
  QA_ADVANCED="$(jq -r --arg id "$SELECTED_SPEC" --arg sha "$CODE_HEAD" '
    if (.id == $id and .head_sha == $sha
        and (.qa_outcome | IN("SHIP","NEEDS_WORK","NA","BLOCKED")))
    then "true" else "false" end' "$QA_RECEIPT" 2>/dev/null || echo false)"
fi
```

Echo the evidence block:

```text
Evidence:
stage=qa
qa_outcome=<SHIP|NEEDS_WORK|NA|BLOCKED|->
head_sha=<receipt head_sha or ->
advanced=<true|false>
```

What follows a fresh `qa_outcome` (`QA_ADVANCED=true`) is owned by `references/gate-selection.md`.

QA commits its receipt and filed bug-memory entries before returning (§6.3b). Flow adds no commit.

A missing or stale receipt (`QA_ADVANCED=false`) is the healthy-no-advance path (Phase 6 strike), never a crash. The QA skill ran but produced no fresh verdict. Freshness is `references/qa-stage.md`'s rule; what each outcome does next is `references/gate-selection.md`'s.

For `make-pr`, advancement means a gh-confirmed OPEN PR URL for the branch. There is no flowctl transition for make-pr, and a successful PR hop must never record a strike. Capture the probe's exit status separately from the parse: a bare `gh | jq | head` pipeline returns `head`'s zero status and an empty URL when `gh` itself fails, which would turn an outage or auth failure into a healthy-no-advance strike:

```bash
PR_VERIFY_FAILED=0
PR_VERIFY_JSON=$(gh pr list --head "$BRANCH_NAME" --state all --json url,state,number --limit 10 2>/dev/null) || PR_VERIFY_FAILED=1
OPEN_PR_URL=$(printf '%s\n' "${PR_VERIFY_JSON:-[]}" | jq -r 'first(.[] | select(.state == "OPEN") | .url) // empty' 2>/dev/null) || PR_VERIFY_FAILED=1   # jq is the status-bearing command: no trailing `head` to mask a parse error
```

`PR_VERIFY_FAILED=1` (gh missing, unauthenticated, API error, or unparseable output) is crash-class: `PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=make-pr reason="gh probe failed at make-pr verify"`, no strike. Only a clean probe with no OPEN row is the healthy-no-advance path.

Echo the URL when present:

```text
Evidence:
stage=make-pr
open_pr.before=-
open_pr.after=<url>
advanced=<url present>
```

If the post-dispatch tree is dirty outside `.flow/`, stop with `NEEDS_HUMAN` and leave state for diagnosis. This is a crash-class outcome, not a strike, and it ends the run before any further hop.

If the sub-skill emitted a `Tracker sync:` summary line, pass that line through in the evidence echo. The run never re-checks the tracker itself.

Done when: every dispatched stage's before/after evidence block and `stage:` outcome line are in the transcript, each `advanced` was decided from re-read state rather than sub-skill narration, and the post-hop dirty-tree guard passed.

## Phase 3.5 - ASK (backlog mode only, non-workable subjects)

**Active only when `PILOT_AUTONOMY=backlog` AND Phase 1.6 routed the subject to `ask`** (ready-but-thin / needs-spec / needs-human / force-gated). Execute [references/backlog-mode.md](references/backlog-mode.md) Phase 3, the async question valve. **Never asks interactively** (`AskUserQuestion` is forbidden on the run path; the human answers later via the spec or the tracker).

**Enforce invariant #2 inline before any spec-side write.** A spec-backed subject writes `## Open Questions`; a tracker-only subject (empty/absent `SPEC_PATH`) must hard-exit rather than author a spec stub. Call the assert with the resolved paths:

```bash
# Spec-backed: SPEC_PATH points at an EXISTING spec file -> the assert passes and the op writes the
# `## Open Questions` anchor. Tracker-only: SPEC_PATH is empty -> the assert hard-exits, so the op is
# invoked WITHOUT touching any spec (the question lives in the tracker comment alone). Run the assert
# ONLY when a spec-side write is intended (HAS_SPEC=1); a tracker-only subject skips it and parks in
# the tracker.
if [ "${HAS_SPEC:-0}" = "1" ] && { [ -z "$SPEC_PATH" ] || [ ! -f "$SPEC_PATH" ]; }; then
  echo "Evidence: backlog mode attempted to author a spec for a specless item ($SUBJECT_ID)"
  echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=ask reason="backlog mode never authors specs — surfaced as needs capture/refine gap"'
  exit 1
fi
```

Backlog mode: post and park per backlog-mode.md §Phase 3, ending `ASKED`.

## Phase 6 - REPORT + strikes ledger

A `land` stage uses `references/tail.md`'s verdict mapping and cadence, never the healthy-no-advance strike path below. Keep the pilot ledger untouched on a landing wait or blocker; a verified advance may clear it. A confirmed merge ends the run with `ADVANCED`, including when the tracker touchpoint failed.

On `ADVANCED`, if the snapshot has a strike for the selected spec, clear it with `$FLOWCTL pilot strikes clear "$SELECTED_SPEC" --json`. Do not clear an absent entry.

Then apply the continuation rule in "The hop loop" above.

When the run ends, print the terminal line. `stage=` names every dispatched stage in order joined by `+`; the reason names the last hop's outcome. For a **chained** spec (SELECT's `CHAIN_PARENT` non-empty) the reason starts with `chained on <parent-id>; ` followed by the existing reason text; a non-chained run prints byte-identical lines.

```bash
# fence:verdict-reason — inputs: CHAIN_PARENT (SELECT's `spec chain` .parent, empty when not chained), REASON (the existing reason text)
[[ -n "${CHAIN_PARENT:-}" ]] && REASON="chained on $CHAIN_PARENT; $REASON"
```

```text
PILOT_VERDICT=ADVANCED spec=<id> stage=<stage> reason="<what advanced>"
```

For a `qa` stage the reason names the fresh `qa_outcome` so a transcript-only driver sees the result without re-reading the receipt, e.g. `reason="qa pass: qa_outcome=NEEDS_WORK - findings surfaced on the PR"` or `reason="qa pass: qa_outcome=BLOCKED - no local app reachable, advancing"`. Only a *missing/stale* receipt routes to the healthy-no-advance strike below.

Complete each stage's ledger update before recording the next stage's result:

```text
PILOT_VERDICT=ADVANCED spec=<id> stage=work+qa+make-pr reason="make-pr: open PR <url>"
```

A `make-pr` that yields no open PR strikes under `make-pr` exactly as a standalone tick would; a driver grepping `PILOT_VERDICT=ADVANCED` keeps working.

On healthy-but-no-advance, record the cumulative strike and unready at two in one locked operation:

```bash
STRIKE_JSON="$($FLOWCTL pilot strikes record "$SELECTED_SPEC" --stage "$STAGE" --reason "$NO_ADVANCE_REASON" --json)" || exit 1
STRIKE_COUNT="$(printf '%s' "$STRIKE_JSON" | jq -r '.count')"
```

If `STRIKE_COUNT` is `1`, leave the spec ready, end the run, and print:

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="no advancement (strike 1/2): <why>"
```

If `STRIKE_COUNT` is `2` or greater, the command has unreadied the spec; keep the ledger reason and print:

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="no advancement (strike 2/2, spec unreadied): <why>; clear with: flowctl pilot strikes clear <id>"
```

The recovery clause is part of the reason string, not a separate line: a strikeout is the one terminal a human must undo by hand, and on a repo with `tracker.readyState` armed the board cannot undo it (Phase 1 item 3), so the transcript-only driver or human reading this verdict gets the exact command. Keep it last in the reason, after `<why>`.

Backlog mode: see backlog-mode.md §Backlog-mode dep-wait `BLOCKED` terminal.

Crash-class outcomes are `NEEDS_HUMAN`: sub-skill crash, dirty non-`.flow/` tree after dispatch, gh probe failure in the all-done branch or at the make-pr verify (`PR_VERIFY_FAILED=1`), branch inconsistency, closed-without-merge PR (with no merged PR on the branch), merged-PR-with-nothing-new-beyond-its-head, stale in-progress-only claim, a review that exits `NOT_RETRYABLE`, or autonomy ambiguity. Leave state untouched and record no strike:

```text
PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=<stage> reason="<one line>"
```

Without current landing authority, an all-done spec with an **open** PR is *not* crash-class; it is the benign `DEFERRED_TO_LAND` terminal below (land owns the merge). Authorized landing and confirmed-merge reporting use `references/tail.md` instead of these default terminals. Only the closed-unmerged-with-no-merged-PR, missing-branch, and merged-with-nothing-new (branch head equals the newest merged PR head) all-done states are `NEEDS_HUMAN`; merged plus commits beyond that head classifies `make-pr` even when older closed PRs share the branch. An open all-done spec with **no** PR and no previously bound target is not terminal; `references/route-matrix.md` names what it dispatches.

Terminal verdict when no spec was dispatched, split by why. **The two cases stay distinct**; a run that reported an all-done-with-open-PR spec as `NO_WORK` has broken this:

- **No selectable candidate at all** (none open+ready, or all skipped for unsatisfied deps / other-actor claims) yields `NO_WORK`:

  ```text
  PILOT_VERDICT=NO_WORK spec=- stage=- reason="no ready spec with satisfied deps"
  ```

- **Every remaining candidate was deferred to land** (each all-done with an existing OPEN PR, the only reason they weren't dispatched) yields the distinct, greppable `DEFERRED_TO_LAND` verdict, naming the deferred spec so a transcript-only driver can hand it to `/flow-next:land`. A `DONE`-but-open-PR spec is real outstanding work that land owns, not absence of work.

  ```text
  PILOT_VERDICT=DEFERRED_TO_LAND spec=<id> stage=land reason="all tasks done, open PR <url> — land owns the merge"
  ```

  When more than one candidate was deferred, name the first deferred spec (stable id order) in the line; the reason still reads `defer to land`.

Backlog mode: see backlog-mode.md §Backlog-mode decision log.

Done when: the ledger reflects this hop (cleared on `ADVANCED`, incremented on healthy-no-advance, untouched on crash-class), one decision-log row per dispatched stage was appended, and either the next hop has started or the terminal verdict line is printed.

The `PILOT_VERDICT` line is always the last line of the run's output. Print nothing after it.
