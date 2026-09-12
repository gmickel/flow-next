# /flow-next:flow --auto - the unattended driver

Read only when SKILL.md parsed the exact `--auto` token. One run selects one ready spec and drives it through `workflow.md`'s hop (Step 2 route, Step 3 run the stage, Step 4 re-evaluate) until a terminal, or through exactly one hop under `--tick`. Every run ends with one `PILOT_VERDICT` line.

## Preamble

`$FLOWCTL` is the value SKILL.md's preamble established; this file defines no second copy.

Shared shell context for the run:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODAY="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

`jq`, `git`, and `gh` must be on PATH when classification reaches the all-done PR branch.

Cold session or run start: `$FLOWCTL brief` first for session-scope orientation (one budgeted call).

**Re-read this file at every run start.** A long `/loop` run executing from a stale in-context copy drifts from the file the repo ships; the file on disk is the contract, the remembered copy is not.

**Check an idle dispatched agent through its commits, receipts, and status fields.** Sending it a resume message restarts it, so a merely slow agent becomes two runs.

## Hard guards (before anything else)

Run these guards before selection, ledger writes, branch changes, or skill dispatch. `--auto` refuses only under Ralph; it does not refuse under `FLOW_AUTONOMOUS` or `mode:autonomous`, because it sets those for the stages it dispatches.

```bash
if [[ -n "${FLOW_RALPH:-}" || -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  echo "Ralph and pilot are alternative drivers — never nest them" >&2
  echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="nested under Ralph harness (FLOW_RALPH/REVIEW_RECEIPT_PATH set) — refuse to run"'
  exit 1
fi

if git -C "$REPO_ROOT" status --porcelain | grep -v '^.. \.flow/' >/dev/null; then
  echo "Evidence: dirty non-.flow working tree at run start"
  git -C "$REPO_ROOT" status --porcelain | grep -v '^.. \.flow/' || true
  echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="dirty working tree at tick start"'
  exit 0
fi
```

Dirty tree means dirty outside `.flow/`; the run leaves state untouched. No cleanup, no claim reset, no strike. The same dirty-tree guard runs again after every hop (Phase 5).

Resolve the strikes ledger after both hard guards, READ-ONLY here (a missing file reads as `{}`; nothing is created or written until a write site in Phase 1 or Phase 6, so `--explain` leaves the filesystem untouched). It lives under the git common dir so it is shared across worktrees and cannot be swept into commits by `git add -A`:

```bash
LEDGER_DIR="$(git -C "$REPO_ROOT" rev-parse --git-common-dir)/flow-next"
LEDGER="$LEDGER_DIR/pilot-strikes.json"
LEDGER_JSON="$(cat "$LEDGER" 2>/dev/null || echo '{}')"
```

Ledger schema: `{"<spec-id>": {"count": <n>, "stage": "<stage>", "reason": "<one line>", "ts": "<iso8601>"}}`. Ownership is shared: flowctl owns READ and CLEAR (`flowctl pilot strikes list`, `flowctl pilot strikes clear <spec-id>`, `clear --all`) so a human has a deterministic recovery that does not mean hand-editing a file under `.git/`; this file keeps the write sites that RECORD strikes. Every write site runs `mkdir -p "$LEDGER_DIR"` plus `[ -s "$LEDGER" ] || echo '{}' > "$LEDGER"` first, then writes atomically with `jq` plus `mv`.

## Arguments

Retain an explicit request in the current user message to review the selected spec's design before work (for example, "flow --auto fn-12; review its design first") as host context for CLASSIFY. This intent is separate from argument parsing and `--review`, which selects a backend; it expires with this run.

Parse `$ARGUMENTS` for the scope lock, the shape, the explain switch, and passthroughs. `--auto` never accepts intent, a path, a branch, or free text. The ready flag is the consent boundary and there is no capture upstream of it. Unknown flags warn to stderr and are ignored. Defaults are `research=grep`, `depth=short`, and `review` resolved later via `$FLOWCTL review-backend`.

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
    --auto)       : ;;                         # consumed by SKILL.md mode detection
    --tick)       AUTO_TICK=1 ;;
    --review|--research|--depth) PREV="$ARG" ;;
    --explain|--dry-run) PILOT_DRY_RUN=1 ;;
    --backlog)    PILOT_BACKLOG_OVERRIDE=1 ;;
    --review=*)   PILOT_REVIEW="${ARG#--review=}" ;;
    --research=*) PILOT_RESEARCH="${ARG#--research=}" ;;
    --depth=*)    PILOT_DEPTH="${ARG#--depth=}" ;;
    -*) echo "Unknown flag: $ARG (ignored by /flow-next:flow --auto)" >&2 ;;
    fn-*) [ -z "$PILOT_SPEC" ] && PILOT_SPEC="$ARG" || echo "Unknown argument: $ARG (ignored by /flow-next:flow --auto)" >&2 ;;
    *)  echo "Unknown argument: $ARG (ignored by /flow-next:flow --auto)" >&2 ;;
  esac
done
[[ -n "$PREV" ]] && echo "Flag $PREV given without a value (ignored by /flow-next:flow --auto)" >&2
export PILOT_SPEC PILOT_DRY_RUN PILOT_REVIEW PILOT_RESEARCH PILOT_DEPTH PILOT_BACKLOG_OVERRIDE AUTO_TICK
```

No branch flag exists. Branch resolution is run-owned from the selected spec's `branch_name`.

There is no `--no-plan` flag: the accepted choice is the spec's `no_plan` field, set at capture, by attended flow, by work before mint, or by this run's route recording (Phase 2). A stray `--no-plan` gets the unknown-flag notice; the run never infers consent from a flag. Intentional plans and explicit design-review requests remain authoritative.

### Autonomy mode resolution - gate the wide backlog behavior

Resolve `PILOT_AUTONOMY` once, here, so every downstream block keys off a single value. This block also captures the run's ROOT CONFIG SNAPSHOT, the ONLY `config get` invocation across this file and its references: the `pipeline.qa`, `pipeline.chainStages`, and `pilot.gateClasses` reads derive from the snapshot file via jq, never a second config call. The gate is a **strict scalar string-enum**: backlog mode activates **only** on the literal `backlog` (config `pilot.autonomy`), or when the per-run `--backlog` flag forced the override. Any other config value (`ready`, `null`, a coerced bool `true`, a typo) leaves the run in `ready` mode, byte-for-byte unchanged (`references/backlog-mode.md` is never even read):

```bash
# Root config snapshot: {"key":null,"value":{<merged config>}}. Persisted to a file
# because bash vars do not survive across prompt turns; later fences RECOMPUTE this
# same deterministic repo-hash-keyed path and jq it. The path lives under
# ${TMPDIR} - NEVER under repo-controlled .flow/tmp (autonomous symlink safety:
# a committed symlink must not redirect this write out of tree) - so an explain
# run mutates nothing inside the repo; explain terminals also `rm -f` this
# snapshot, leaving no persistent scratch state. On capture FAILURE remove the
# file: downstream jq reads then error, which keeps the pipeline.qa probe's
# fail-open contract (probe error => ACTIVE) intact.
PILOT_CFG_SNAPSHOT="${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json"
rm -f "$PILOT_CFG_SNAPSHOT" 2>/dev/null   # drop any stale/planted file (incl. a symlinked leaf) before the fresh write
$FLOWCTL config get --json > "$PILOT_CFG_SNAPSHOT" 2>/dev/null \
  || rm -f "$PILOT_CFG_SNAPSHOT"
PILOT_AUTONOMY="$(jq -r '.value.pilot.autonomy' "$PILOT_CFG_SNAPSHOT" 2>/dev/null)"
if [ "$PILOT_BACKLOG_OVERRIDE" = "1" ]; then
  PILOT_AUTONOMY="backlog"                       # --backlog forces backlog this run
elif [ "$PILOT_AUTONOMY" != "backlog" ]; then
  PILOT_AUTONOMY="ready"                         # ONLY the literal `backlog` enables - never bool true / typos / null
fi
export PILOT_AUTONOMY
```

When `PILOT_AUTONOMY=ready` (the default), the run behaves exactly as Phases 1 to 6 below describe; no backlog-mode code path runs and `references/backlog-mode.md` is not loaded. When `PILOT_AUTONOMY=backlog`, **read [references/backlog-mode.md](references/backlog-mode.md) top to bottom, execute its backlog-only setup, then continue with Phase 1**. The reference owns the backlog-only verdict extension plus SELECT/TRIAGE/ASK context; this file keeps the enforcing guards and action sites. In long-horizon mode a backlog run drives its one selected item to a terminal, then stops; the next invocation selects the next item.

## The verdict contract (read this before the phases)

The `/goal` validator is transcript-blind. It reads conversation output only and never runs tools. Every hop therefore echoes its verification evidence into the output (flowctl status fields, task counts, task status transitions, and the gh-confirmed PR URL for make-pr).

Every run ends with exactly one terminal line, the last line of the response, with nothing after it. The common ready-mode grammar is:

```text
PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"
```

Use `spec=-` and `stage=-` when no spec was selected. Stage values are exactly `plan`, `plan-review`, `work`, `qa` (when the QA gate selected it), `make-pr`, `land`, or `-`. A run that dispatched more than one stage names every dispatched stage in order joined by `+` (for example `stage=work+qa+make-pr`) and carries the last hop's verdict; a chained tick under `pipeline.chainStages` is the same shape, exactly `qa+make-pr`. A `--tick` run names one stage.

**Explain snapshot cleanup.** Under `--explain` (`PILOT_DRY_RUN=1`), at EVERY terminal `PILOT_VERDICT` emission (the classification stop, the diagnostic `TRIAGED` exit, every `NO_WORK` / `DEFERRED_TO_LAND` / hard-guard exit) remove the root config snapshot BEFORE printing the verdict, so an explain run leaves no persistent scratch state:

```bash
rm -f "${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json"
```

Recompute the path exactly as above (vars die across prompt turns). Live runs keep the snapshot for the run's remaining fences; it is overwritten fresh by the next run's capture. Never blocks, fail-open (`rm -f` on a missing file is a no-op).

`DEFERRED_TO_LAND` is a distinct *non-terminal-work* verdict (stage `land`): every remaining all-done candidate has an open PR that land, never this run, owns. It is deliberately separated from `NO_WORK` so a driver can route it to `/flow-next:land` instead of stopping; an all-done spec with an open PR is real outstanding work, never absence of work.

Driver condition examples (the default recipe is one `flow --auto` per item; the tick shape is for hosts without stable long sessions):

```text
/goal keep running /flow-next:flow --auto until it prints PILOT_VERDICT=NO_WORK, or stop after 20 turns
/goal keep running /flow-next:flow --auto --tick --review=codex until PILOT_VERDICT=NO_WORK or PILOT_VERDICT=NEEDS_HUMAN
```

## Forbidden

- Asking the user anything on the run path. The run is autonomous; ambiguity maps to `NEEDS_HUMAN`. In backlog mode, ambiguity that needs a person is surfaced **async** via the `ask` stage (`ASKED`), never an interactive `plain-text numbered prompt`. `references/prototype-before-ask.md` licenses no plain-text numbered prompt here: an unattended fork that is not observable is `NEEDS_HUMAN` in ready mode and `ASKED` in backlog mode; an observable fork may be settled by running something only inside the dispatched stage's existing license, never by the run itself.
- Dispatching any skill outside the stage set `{plan, plan-review, work, qa, make-pr}`, with `qa` only when `references/gate-selection.md` selected it for this hop. **Backlog mode (`PILOT_AUTONOMY=backlog`) additionally invokes `/flow-next:tracker-sync` for the `reconcile` / `list-open` / `list-comments` / `list-relations` / `question` ops**, read/surface-only tracker calls (`list-comments` reads parked question rounds; `list-relations` reads dependency relations for dep-ordering), never a pipeline stage, and only on the backlog path. Capture, refine, chart, resolve-pr, merge, and release are **never** stages of this run (capture/refine/chart are human authoring and discovery upstream of the consent boundary; resolve-pr/merge/release are land's territory downstream of the PR). **`qa` under its gate and `tracker-sync` under backlog mode set no precedent for any of those**; a run that dispatched one of them by analogy has broken this.
- Dispatching two stages in one hop. Each hop dispatches exactly one stage; the next hop re-classifies from observed state. The one exception is `--tick` under `pipeline.chainStages==on`: `make-pr` after this tick's `qa` verified a fresh terminal verdict (Phase 5, Chained stage), which is the `qa+make-pr` tick the deprecated key still buys for one release.
- Re-implementing sub-skill logic. This file owns selection, classification glue, dispatch, verification, verdicts, and the strikes ledger only. The backlog-mode SELECT/TRIAGE/ASK workflow lives in `references/backlog-mode.md` (loaded only when `PILOT_AUTONOMY=backlog`); the question-anchor authoring plus answer round-trip live in tracker-sync; backlog mode invokes them, never re-implements them.
- **Never merging / never invoking land.** In either mode the terminus is `make-pr` (draft). Merge stays human-gated. Backlog mode never calls `/flow-next:land`, `gh pr merge`, or any merge path. The run never dispatches a second driver.
- **Never authoring a spec** (backlog mode). `capture`/`refine` are human-gated upstream. A missing or too-thin spec is surfaced as a "needs capture/refine" gap and parked (`ASKED`), never auto-written. The only writing the `ask` stage may do is fill an obvious blank in an *existing* spec, never create a spec stub from a bare ticket.
- Touching gh anywhere except the all-done classification branch's PR probe, the plan/plan-review branch row's open-PR probe, and the make-pr verification probe.
- Printing anything after the `PILOT_VERDICT` line.
- Running under Ralph (`FLOW_RALPH` / `REVIEW_RECEIPT_PATH`).

## Review no-repeat terminal

When a delegated plan, implementation, or completion review exits `1` with `NOT_RETRYABLE: artifact unchanged since last verdict`, emit `PILOT_VERDICT=NEEDS_HUMAN` and end the run. It is human action (edit the artifact, explicit reset, or deliberate `--force`), never a retry/transport refund, autonomous reset/force, or redispatch. Review-counter reset and `--force` review dispatch/increment are human-only recovery tools.

## The hop loop

Run workflow.md Steps 2 to 4 with the unattended guards, branch resolution, evidence, and ledger actions in Phases 2 to 6 below. Selection (Phase 1) runs once per run and fixes the item. After Phase 6:

- `AUTO_TICK=1`: print the terminal line and stop.
- `AUTO_TICK=0` and the hop ended `ADVANCED` with a stage other than `make-pr`: append the stage to `DISPATCHED_STAGES` (joined by `+`), re-run the dirty-tree guard, reload `LEDGER_JSON`, and return to Phase 2 for the same spec.
- `AUTO_TICK=0` and the hop ended `ADVANCED` with `make-pr`: the PR exists; print the terminal line and stop.
- Any other outcome (`NEEDS_HUMAN`, `ASKED`, `BLOCKED`, `DEFERRED_TO_LAND`, `NO_WORK`) ends the run; only `ADVANCED` continues.

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
  # unattended (plain-text numbered prompt is never reached). Load backlog-mode.md (the
  # agentic SELECT/TRIAGE/ASK workflow) now; Phase 1.5 / 1.6 / 3.5 execute it.
  export FLOW_AUTONOMOUS=1

  # Invariant #1 - never merge / never invoke land. The ONLY skills a backlog
  # run may invoke are the pipeline stages {plan, plan-review, work, qa, make-pr}
  # plus the tracker-sync surfacing/read ops {reconcile, list-open, list-comments,
  # list-relations, question}. These tracker ops only read or surface a question;
  # none merges, lands, or resolves, so the never-merge guard is unaffected.
  # `list-relations` is the per-issue listIssueRelations READ that 1e needs for
  # tracker dep edges. Called inline immediately before EVERY dispatch (Phase 1.5
  # tracker ops, Phase 3.5 ask, Phase 4 stage dispatch) with the about-to-run
  # slash command.
  assert_allowed_dispatch() {  # $1 = the slash command about to be invoked
    case "$1" in
      /flow-next:plan|/flow-next:plan-review|/flow-next:work|/flow-next:qa|/flow-next:make-pr) return 0 ;;
      "/flow-next:tracker-sync reconcile"*|"/flow-next:tracker-sync list-open"*|"/flow-next:tracker-sync list-comments"*|"/flow-next:tracker-sync list-relations"*|"/flow-next:tracker-sync question"*) return 0 ;;
      *)
        echo "Evidence: backlog mode attempted a forbidden dispatch ($1)"
        echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="backlog mode dispatch allowlist — never merges/lands/resolves (R6)"'
        exit 1 ;;
    esac
  }

  # Invariant #2 - never author a spec. The ask stage may write spec-side ONLY when
  # the spec file ALREADY exists (fill an obvious blank in an existing spec). A
  # tracker-only item has NO spec; its question parks in the tracker comment ALONE.
  # Called inline in Phase 3.5 before any spec-side write.
  assert_spec_write_allowed() {  # $1 = SUBJECT_ID, $2 = SPEC_PATH (empty for tracker-only)
    if [ -z "$2" ] || [ ! -f "$2" ]; then
      echo "Evidence: backlog mode attempted to author a spec for a specless item ($1)"
      echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=ask reason="backlog mode never authors specs — surfaced as needs capture/interview gap (R3/R4)"'
      exit 1
    fi
  }
fi
```

**Ready mode is byte-for-byte unchanged**: the gate-off branch is a bare `:` no-op. No backlog block below runs, `references/backlog-mode.md` is never loaded, `FLOW_AUTONOMOUS` is never exported, and the verdict grammar and stage set match the ready-mode contract exactly.

### Backlog safety invariants - enforcing guards, not prose

The four invariants are **hard bash branches enforced inline at their real site** (an executing agent, and a reviewer, reads the snippet as authoritative). Each short-circuits a forbidden action with a parseable terminal line; none is advisory prose. The two assert helpers above are defined only in the backlog branch and called inline at the dispatch and ask sites; invariants #3/#4 are enforced where selection happens (Phase 1.5):

- **Invariant #1 (never merge/land)** is enforced by `assert_allowed_dispatch "$DISPATCH_TARGET"` called inline immediately before **every** dispatch: the Phase 1.5 tracker-sync ops, the Phase 3.5 `question` op, and the Phase 4 stage dispatch. A `/flow-next:land`, `gh pr merge`, or `/flow-next:resolve-pr` never reaches the allowlist's `return 0`.
- **Invariant #2 (never author a spec)** is enforced by `assert_spec_write_allowed "$SUBJECT_ID" "$SPEC_PATH"` called inline in Phase 3.5 **before any spec-side write**; a tracker-only (empty/absent `SPEC_PATH`) subject hard-exits rather than creating a spec stub.
- **Invariant #3 (single item per run)** is enforced in Phase 1.5 by the `SELECTED_COUNT` assertion: selection picks exactly **one** `SUBJECT_ID`; a `SELECTED_COUNT != 1` is a hard error, and there is no `for item in candidates` advance/park loop anywhere downstream. The hop loop drives that one item; it never selects a second.
- **Invariant #4 (dep cycle/deadlock surfaces)** is enforced in Phase 1.5e by the `DEP_DEADLOCK` branch: an un-placeable circular/unsatisfiable dep routes to `ASKED` / `BLOCKED` with a terminal verdict, never falls through to be re-picked next run.

## Phase 1 - SELECT (two-pass)

**Ready mode only.** This two-pass selection runs when `PILOT_AUTONOMY=ready` (the default). In **backlog mode** Phase 1.5's wide SELECT replaces it entirely (it reuses the same dependency / claim / re-bless checks but widens the candidate set and acts on the skip pile instead of dropping it to `NO_WORK`). Skip directly to Phase 1.5 when `PILOT_AUTONOMY=backlog`.

Pass 1 enumerates minimal candidates:

```bash
SPECS_JSON="$($FLOWCTL specs --json)"
```

Candidate predicate for pass 1:

- `status == "open"`.
- ready flag is set.
- stable id order.
- if a spec id was provided, the candidate list is exactly that spec and it still must pass the predicate.

Echo the pass-1 counts: total specs, open specs, ready specs, and scope-lock target if present.

Pass 2 loads full spec JSON for each candidate:

```bash
SPEC_JSON="$($FLOWCTL show "$candidate" --json)"
TASKS_JSON="$($FLOWCTL tasks --spec "$candidate" --json)"
```

Apply the full predicate:

1. Dependencies: every `depends_on_epics[]` value is satisfied iff `$FLOWCTL show <dep> --json` reports `status == "done"`. Any unsatisfied dependency skips the candidate and records `deps unsatisfied: <ids>`.
2. Collision avoidance: no task may be `in_progress` and assigned to another actor. The minimal `tasks --spec` listing carries no `assignee`; for every task with `status == "in_progress"`, fetch `$FLOWCTL show <task-id> --json` and read its `assignee` field. Resolve this session's actor identity exactly as `flowctl.get_actor()` does: `$FLOW_ACTOR` env var, else `git config user.email`, else `git config user.name`, else `$USER`, else `unknown`. If resolution bottoms out at `unknown`, any non-empty assignee counts as another actor.
3. Strikes: a ledger entry with `count >= 2` normally means the spec was unreadied after failure, but a candidate that is ready again has been human re-blessed. Clear that ledger entry (write site: `mkdir -p "$LEDGER_DIR"`, seed if missing, then atomic `jq` plus `mv`) and treat the spec as fresh. Under `--explain`, do not write; report the entry as would-clear in the classification report instead. **Exception, active `tracker.readyState` projection:** backlog 1a re-projects `ready=true` from the board on **every run**, so a "ready again" under a configured `tracker.readyState` is mechanical, not a human re-bless. Clearing the strike on it would re-dispatch the same failing spec every run forever, defeating the strike limit. **So with `tracker.readyState` set, a `count >= 2` strike survives a projection-set ready**: the strikeout stands (skip the candidate as still-struck) until the human who answered the surfaced failure runs `flowctl pilot strikes clear <spec-id>`. That verb is THE recognized human clear under an armed `tracker.readyState`; no board state can serve as one, because a deliberate out-and-back move and a projection echo are byte-identical in every durable artifact, so "an explicit re-ready" is not something this run can detect. A cleared strike whose only "re-bless" was a board-set ready has broken this. The `BLOCKED spec=… reason="strike 2/2"` terminal names the verb, so the transcript carries its own recovery.
4. **No gh touch here.** PR state belongs exclusively to the all-done classification branch; a gh call in SELECT has broken this.

```text
PILOT_VERDICT=NO_WORK spec=- stage=- reason="no ready spec with satisfied deps"
```

Done when: exactly one candidate has passed the full predicate, or none has and the terminal above applies.

## Phase 1.5 - SELECT (wide, backlog mode only)

**Active only when `PILOT_AUTONOMY=backlog`.** Execute the SELECT workflow in [references/backlog-mode.md](references/backlog-mode.md) Phase 1 (1a to 1g); its mechanics are authoritative and single-sourced there. What stays here is the enforcing bash: the explain gate, the guarded dispatches, and the invariants.

**`--explain` is dispatch-free.** An explain backlog run is inspection-only: **it dispatches nothing and mutates nothing**, no readiness projection, no receipts. An explain run that fired a tracker-sync op has broken this. So when `PILOT_DRY_RUN=1`, **skip the tracker-sync `reconcile` (1a) and `list-open` (1c) dispatches entirely** and select from the **flow-side `ready --all` facts alone**; then Phase 1.6 classifies and the run stops with the diagnostic `TRIAGED` line (no `ask`, no pilot-log row). The gate below wraps every Phase 1.5 dispatch:

```bash
DRY="${PILOT_DRY_RUN:-0}"   # 1 => inspection-only: no tracker-sync dispatch, flow-side facts only
```

1. **1a - pull-before-scan** (backlog-mode.md 1a). **Skipped under `--explain`** (dispatch-free; the explain readiness read is whatever `ready --all` already reflects locally). Otherwise guard the dispatch (invariant #1), then dispatch:

   ```bash
   if [ "$DRY" = "0" ]; then
     DISPATCH_TARGET="/flow-next:tracker-sync reconcile"; assert_allowed_dispatch "$DISPATCH_TARGET"
     # -> dispatch: /flow-next:tracker-sync reconcile mode:autonomous   (FLOW_AUTONOMOUS=1; no-op when the bridge is inactive)
   fi
   ```

2. **1b - scan the flow side (facts)** (backlog-mode.md 1b): `READY_ALL_JSON="$($FLOWCTL ready --all --json)"`.

3. **1c - union the tracker side (`list-open`)** (backlog-mode.md 1c). **Skipped under `--explain`**; the candidate set is then the flow specs (1b) only. Otherwise guard the dispatch (invariant #1), then dispatch:

   ```bash
   if [ "$DRY" = "0" ]; then
     DISPATCH_TARGET="/flow-next:tracker-sync list-open"; assert_allowed_dispatch "$DISPATCH_TARGET"
     # -> dispatch: /flow-next:tracker-sync list-open mode:autonomous   (no-ops when tracker.readyState unset -> flow-ready specs only)
   fi
   ```

4. **1d - skip parked subjects** (backlog-mode.md 1d). For every tracker-only candidate, guard and execute the missing comment read before deciding whether its latest question round is parked:

   ```bash
   if [ "$DRY" = "0" ]; then
     DISPATCH_TARGET="/flow-next:tracker-sync list-comments"; assert_allowed_dispatch "$DISPATCH_TARGET"
     # -> dispatch per tracker-only issue: /flow-next:tracker-sync list-comments <tracker-id> mode:autonomous
     # Any error or truncated listing fails closed: do not select from an
     # incomplete question/answer history.
   fi
   ```

5. **1e - dep-order the survivors** (backlog-mode.md 1e). The tracker relation edges come from the guarded per-issue `list-relations` READ (invariant #1: on the allowlist, never a merge):

   ```bash
   if [ "$DRY" = "0" ]; then
     # For each TRACKER candidate, read its relations to add the tracker dep edges.
     DISPATCH_TARGET="/flow-next:tracker-sync list-relations"; assert_allowed_dispatch "$DISPATCH_TARGET"
     # -> dispatch per tracker issue: /flow-next:tracker-sync list-relations <tracker-id> mode:autonomous
     #   <tracker-id> = the candidate's list-open `issue.identifier` (the display handle:
     #   GitLab indexes /issues/:iid from the <project>#<iid> it carries - a global id is
     #   NOT a valid path index), never the opaque global id.
     #   (the listIssueRelations read; no-op/empty when the bridge is inactive or the issue has no relations)
   fi
   ```

   (Under `--explain` there are no tracker candidates, 1c was skipped, so 1e uses the flow `blockedBy` edges only and issues no tracker read; the guarded dispatch above is skipped.) **Invariant #4: a cycle/deadlock is surfaced, never spun on.** When the topo-sort cannot place the chosen candidate because its dep chain is circular or a dep is itself parked/unsatisfiable, set `DEP_DEADLOCK=1` and route it to a state-changing terminal, never fall through to re-pick it next run:

   ```bash
   if [ "${DEP_DEADLOCK:-0}" = "1" ]; then
     # The unresolvable dependency is surfaced as an async question (Phase 3.5 ask -> ASKED).
     # (A plain unsatisfied-but-acyclic dep is NOT a deadlock; it routes to BLOCKED in Phase 1.6.)
     SUBJECT_ID="$DEADLOCK_SUBJECT_ID"; HAS_SPEC="$DEADLOCK_HAS_SPEC"; SPEC_PATH="$DEADLOCK_SPEC_PATH"
     ASK_REASON="unresolvable/circular dependency — $DEADLOCK_DETAIL"
     # -> fall into Phase 3.5 ASK (terminal ASKED). Selection terminates this run.
   fi
   ```

6. **1f - pick the top actionable item** (backlog-mode.md 1f); it becomes `SUBJECT_ID`, the one item to triage in Phase 1.6.

7. **1g - apply the ready-mode claim / collision / re-bless checks to the picked candidate** (backlog-mode.md 1g) before triage; Phase 1.6 CLASSIFY assumes other-actor `in_progress` claims were already skipped here. Under `--explain`, write no ledger; report a re-bless entry as would-clear instead.

**Invariant #3 (single item per run) is enforced here.** Selection sets exactly ONE `SUBJECT_ID`; there is no `for item in candidates` advance/park loop downstream. **Assign `SELECTED_SUBJECTS` to the chosen subject** (the single id 1f/1g settled on, or empty when the pool yielded none), resolve `SPEC_PATH` (the spec file path when spec-backed, else **empty** for a tracker-only item, whose `SUBJECT_ID` is the candidate's `list-open` `issue.identifier`, the display handle the downstream `list-relations` / `question` dispatches resolve against, never the opaque global id) and `HAS_SPEC`, then hard-assert the count:

```bash
# SELECTED_SUBJECTS = the chosen subject id; selection yields exactly one (or
# empty when no candidate survived 1f/1g). Assign it from SUBJECT_ID here so the
# single-item guard below counts the REAL selection (an unset var would always
# count 0 and wrongly fall through to NO_WORK even after a subject was picked).
SELECTED_SUBJECTS="${SUBJECT_ID:-}"
SELECTED_COUNT="$(printf '%s\n' "$SELECTED_SUBJECTS" | grep -c . )"
if [ "$SELECTED_COUNT" -gt 1 ]; then
  echo "Evidence: backlog selection yielded $SELECTED_COUNT subjects — single-tick contract violated"
  echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="backlog single-tick — selection must pick exactly one item (R6 invariant #3)"'
  exit 1
fi
```

A `SELECTED_COUNT` of 0 (empty `SUBJECT_ID`, no candidate survived 1f/1g) falls through to the terminal split below (`NO_WORK`); exactly 1 proceeds to Phase 1.6.

Done when: `SELECTED_COUNT` is 0 or 1, `SPEC_PATH` / `HAS_SPEC` are resolved for the picked subject, and no dispatch happened under `--explain`.

Fall through to the existing terminal split **only when the pool is genuinely empty of a selectable candidate**; verbatim, backlog mode adds neither verdict:

- **`NO_WORK`**: no signalled, unparked candidate exists at all (and no dep wait to report):

  ```text
  PILOT_VERDICT=NO_WORK spec=- stage=- reason="no signalled, unparked backlog item"
  ```

- **`DEFERRED_TO_LAND`**: every all-done candidate has an open PR (the Phase 6 split, unchanged).

## Phase 1.6 - TRIAGE the selected item (backlog mode only)

**Active only when `PILOT_AUTONOMY=backlog`.** TRIAGE runs **in front of** CLASSIFY: a thin / specless / blocked item never reaches the pipeline. Execute [references/backlog-mode.md](references/backlog-mode.md) Phase 2; its class table and routes are authoritative and single-sourced there (first match wins; **`dep-unsatisfied` is checked BEFORE `workable`**). The classification is the **host agent's READ** of the item, never a flowctl field, never a score, never a regex grader, never a second LLM. flowctl supplied facts (Phase 1.5b); the agent supplies judgment here.

**Optional force-gate.** Read the sibling key `pilot.gateClasses` (an array, NOT `pilot.autonomy.gate`). When the selected item matches a configured gate class (the agent's read, like triage, no scorer), route it to `ask` even when otherwise workable:

```bash
# Derived from the root snapshot - NOT a config get call. The path is RECOMPUTED
# here (deterministic repo-hash key; vars don't survive fences). Tolerate BOTH
# shapes: a JSON array (`["risky"]`) AND a scalar set through the CLI -
# `flowctl config set pilot.gateClasses risky` persists the bare string "risky",
# which `.value[]?` would silently drop. Normalize string->single-class.
PILOT_CFG_SNAPSHOT="${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json"
GATE_CLASSES="$(jq -r '(.value.pilot.gateClasses // empty) | if type=="array" then .[] elif type=="string" then (if startswith("[") then (fromjson | .[]?) else . end) else empty end' "$PILOT_CFG_SNAPSHOT" 2>/dev/null)"
```

An empty/unset `gateClasses` (the default) gates nothing; full-auto is unconditional. A scalar `flowctl config set pilot.gateClasses risky` is read as the single class `risky`; multiple classes use a JSON array.

**The completeness read may only withhold, never force**: a promoted-but-thin item is kicked back with a question, never built into a slop PR, but the read never overrides an explicit ready signal to *force* work, never sets the ready flag, never promotes. A read that started work the human had not promoted has broken this.

**A live triage always resolves to a state-changing terminal**: `ADVANCED` / `ASKED` / `BLOCKED` / `NEEDS_HUMAN`. It never ends on a bare `TRIAGED` no-op line; `TRIAGED <id> <class>` is diagnostic / explain only. Append the matching decision-log row at the resolving terminal (Phase 6).

**Explain is the only case that emits `TRIAGED`, and it short-circuits every route.** Under `--explain` (`PILOT_DRY_RUN=1`), backlog triage classifies the subject and stops; an explain run that reached Phase 2 CLASSIFY, Phase 3.5 ASK, the `BLOCKED` terminal, or the Phase 6 pilot-log row has broken this. This branch runs immediately after the class is resolved, before any routing:

```bash
if [ "${PILOT_DRY_RUN:-0}" = "1" ]; then
  # $TRIAGE_CLASS = the class resolved above (workable | ready-but-thin | needs-spec | dep-unsatisfied | needs-human).
  # Explain leaves NO persistent scratch state: remove the root config snapshot (recomputed path).
  rm -f "${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json"
  echo "PILOT_VERDICT=TRIAGED spec=$SUBJECT_ID stage=triage reason=\"dry-run: classified $TRIAGE_CLASS, nothing dispatched or parked\""
  exit 0
fi
```

When NOT explaining, route by class: **workable** sets `SELECTED_SPEC="$SUBJECT_ID"` and continues into Phase 2 CLASSIFY (the existing pipeline; the hop loop then drives this one item); every other class skips Phases 2 to 5 and resolves in Phase 3.5 (ask) or directly at Phase 6 (`BLOCKED`). A live run never emits `TRIAGED` (it always lands on a state-changing terminal).

## Phase 2 - CLASSIFY from the routing reference (workflow.md Step 2)

Resolve the review backend before classification:

```bash
if [[ -n "${PILOT_REVIEW:-}" ]]; then
  REVIEW_BACKEND="$PILOT_REVIEW"
else
  REVIEW_BACKEND="$($FLOWCTL review-backend)"   # prints the backend, or ASK when unset
fi
case "$REVIEW_BACKEND" in
  none|ASK|"") REVIEW_CONFIGURED=0 ;;
  *) REVIEW_CONFIGURED=1 ;;
esac
```

Resolve the QA gate value. `pipeline.qa` is the string enum `off | on | auto` that `references/gate-selection.md` defines (any other value is `off`); the value is read once here from the root snapshot and consumed at the all-done juncture. The read is fail-open on a probe/parse error (the freshness reference gets read; the literal check still decides the flags):

```bash
QA_STAGE_ENABLED=0
QA_STAGE_AUTO=0
QA_GATE=""
ACTIVE=0
# Derived from the root snapshot - NOT a config get call. The path is RECOMPUTED
# here (deterministic repo-hash key; vars don't survive fences). A missing or
# unreadable snapshot (removed on capture failure) makes the jq read ERROR, which
# preserves the probe's fail-open contract (error => ACTIVE).
PILOT_CFG_SNAPSHOT="${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json"
QA_GATE="$(jq -r '.value.pipeline.qa' "$PILOT_CFG_SNAPSHOT" 2>/dev/null)" || ACTIVE=1   # snapshot/parse ERROR => ACTIVE (fail open)
[ "$QA_GATE" = "on" ] && ACTIVE=1
[ "$QA_GATE" = "auto" ] && ACTIVE=1
[ "${QA_GATE:-}" = "on" ] && QA_STAGE_ENABLED=1     # the literal `on`: QA on every spec at all-done
[ "${QA_GATE:-}" = "auto" ] && QA_STAGE_AUTO=1      # the literal `auto`: QA when gate-selection.md's drivability read says so
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — read and execute references/qa-stage.md#qa-stage-freshness-probe, then continue with Phase 2 classification."
fi   # default branch: bare no-op - NO link, NO read path
```

When the sentinel prints, read [references/qa-stage.md](references/qa-stage.md), execute its QA-stage freshness probe to compute `QA_FRESH` (and resolve `BRANCH_NAME`), then continue with the classification below. The all-done PR probe's no-PR branch consumes `QA_STAGE_ENABLED` / `QA_STAGE_AUTO` / `QA_FRESH`; on a default run (`off`) the gate is silent and the reference is never read.

Resolve the deprecated stage-chain key. `pipeline.chainStages` is honoured only under `--tick` (the `qa+make-pr` tick it was built for) and is removed with the pilot alias in the next release; in long-horizon mode the hop loop already runs `make-pr` as the next hop, so the key has nothing to chain and is ignored with one notice. Same strict literal-`on` discipline as `pipeline.qa`, derived from the same root snapshot, **no** new `config get`. Unlike the QA probe this read is **fail-closed**: a snapshot/parse error resolves to off, because chaining is an accelerator and the safe degradation is the one-stage tick.

```bash
CHAIN_ENABLED=0
PILOT_CFG_SNAPSHOT="${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json"
CHAIN_STAGES="$(jq -r '.value.pipeline.chainStages' "$PILOT_CFG_SNAPSHOT" 2>/dev/null)" || CHAIN_STAGES=""   # snapshot/parse ERROR => off (fail closed)
if [ "${CHAIN_STAGES:-}" = "on" ]; then
  if [ "${AUTO_TICK:-0}" = "1" ]; then
    CHAIN_ENABLED=1   # ONLY the literal `on` chains, and only under --tick
  else
    echo "pipeline.chainStages is deprecated and ignored under flow --auto (hops run back to back); it still applies under --tick and is removed with the pilot alias next release" >&2
  fi
fi
```

`CHAIN_ENABLED` is consumed by the explain report below and by Phase 5's Chained stage. With `pipeline.qa` off there is never a fresh `qa` stage to chain from, so the switch is inert.

### Route (workflow.md Step 2 runs here)

Step 2 routes the selected spec from `SPEC_JSON`, `TASKS_JSON`, the task details fetched at SELECT, and the design-review intent retained under Arguments: [references/route-matrix.md](references/route-matrix.md) for the spec-state row, [references/gate-selection.md](references/gate-selection.md) for the review, QA, and completion-review gates, and [references/plan-vs-no-plan.md](references/plan-vs-no-plan.md) for a ready spec with no tasks and no recorded route (`no_plan == true` in `SPEC_JSON` is the recorded direct route). Echo the row and the gate section the stage came from. What this run adds:

- **Route echo.** Step 2 records the route it resolved from plan-vs-no-plan.md. Echo `route: direct - <signal absent>` or `route: plan - <the positive signal the rule named>` so a transcript-only driver sees what decided it. Under `--explain` the recording is printed as would-record and nothing is written.
- **Refusal when a selected gate needs a backend the run lacks.** A design review the reference selects (an explicit request, or a recorded `needs_work` / `needs_human` plan review) with `REVIEW_CONFIGURED=0` is `NEEDS_HUMAN`, reason `explicit design review needs a review backend` or `unresolved plan review needs a review backend`. The run never lowers a gate.
- **Resume consent.** The spec's sole direct owner (exactly one task, `implicit_owner == true`, `no_plan == true`) is `in_progress`, its assignee matches this resolved actor (re-read `$FLOWCTL show <owner-id> --json` before admitting), and positive evidence proves its prior run ended (a terminal host session/process record, or an explicit user confirmation of that run's termination): `work`, resuming that owner through spec-level work, with the owner ID and the evidence reference passed as dispatch context. A claim's age, an empty ready list, missing output, or an unassigned claim is not proof; with absent or ambiguous proof keep `NEEDS_HUMAN`, never infer termination or steal a claim.
- **Stale claim.** The only non-`done` tasks are `in_progress` own/unassigned (other-actor claims were already skipped at SELECT) and no resume proof exists: `NEEDS_HUMAN`, reason `stale in-progress claim — work's ready-driven loop cannot resume it`.

### The all-done PR probe

The all-done row of the matrix (tasks done, completion satisfied or ungated) routes to QA per the gate, then make-pr. Before that route runs, the run probes PR state, because an open PR belongs to land and a merged or closed PR changes the answer. This is the only gh touch in classification. Resolve the spec's `branch_name` first (Phase 3 reuses the same `BRANCH_NAME`):

```bash
BRANCH_NAME="$(printf '%s\n' "$SPEC_JSON" | jq -r '.branch_name // empty')"
PR_PROBE_FAILED=0
PR_JSON=$(gh pr list --head "$BRANCH_NAME" --state all --json url,state,number,headRefOid,mergedAt --limit 100 2>/dev/null) || PR_PROBE_FAILED=1
# `--limit` is a fetch cap, not an exhaustion guarantee: a probe that returns
# exactly 100 rows may be truncated, and a truncated history can select the
# wrong merged head. Treat it as probe failure - same NEEDS_HUMAN as a gh error.
[ "$(printf '%s\n' "${PR_JSON:-[]}" | jq 'length')" -ge 100 ] && PR_PROBE_FAILED=1
OPEN_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "OPEN") | .url' | head -1)
CLOSED_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "CLOSED") | .url' | head -1)
MERGED_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "MERGED") | .url' | head -1)
MERGED_HEAD=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '[.[] | select(.state == "MERGED")] | sort_by(.mergedAt) | last | .headRefOid // empty')
```

Outcomes for the all-done branch (evaluate in order, first match wins). The all-done invariant: an all-done / completion-satisfied (`ship` or `not_required`) spec with no **merged** PR, or with merged gate PRs plus commits beyond them, is *unfinished from the board's perspective*; the run keeps driving it (`qa` or `make-pr`), defers it to land (open PR), or surfaces it (`NEEDS_HUMAN`); it never collapses to terminal `NO_WORK`:

- gh missing, unauthenticated, or API failure: `PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=make-pr reason="gh probe failed at all-done branch"`.
- OPEN PR exists: the matrix's open-PR row belongs to land under autonomy (the tail rule's convergence is attended work), so this spec is **deferred to land**: record it as a *deferred candidate* and skip to the next SELECT candidate. This is an explicit defer, never a silent finish: if no later candidate is selectable, the run terminates with the distinct, greppable `PILOT_VERDICT=DEFERRED_TO_LAND` line (Phase 6), never `NO_WORK`. Track the deferred spec id + open-PR url so the terminal line can name it.
- No PR exists: `QA_FRESH=1` or the gate `off` is `make-pr`; otherwise `references/gate-selection.md` decides `qa` or `make-pr` from the gate value, and a skip records `stage: qa - skipped(config: pipeline.qa=auto: <reason>)` in this hop's evidence. This is the all-done, no-PR case (make-pr never ran or its PR was lost); **it always classifies `qa` or `make-pr`**, and a fall-through to `NO_WORK` here has broken this. Echo `qa_gate=<off|on|auto> qa_fresh=<0|1>` in the classification report.
- MERGED PR(s) exist, spec still open, and no OPEN PR (any CLOSED PRs on the branch are irrelevant here; merged work outranks a historical closed PR, so this bullet is evaluated whenever a merged PR exists): compare heads, `git rev-parse <branch_name>` against `MERGED_HEAD` (the `headRefOid` of the merged PR with the greatest `mergedAt`, captured by the probe above). Heads differ: not an inconsistency (merged gate PRs on a reused branch with commits beyond them); classify `make-pr`, subject to the same QA gate as the no-PR bullet (this matches make-pr's Forbidden rule that closed/merged PRs on a reused branch never trigger refusal). Heads equal: `NEEDS_HUMAN` (a merged PR with nothing new and an open spec is the genuinely inconsistent state). Empty `MERGED_HEAD` or rev-parse failure: `NEEDS_HUMAN`, unchanged. Head identity, never ancestry: land squash-merges, so a `rev-list` count against the default branch reads fully-shipped work as unshipped.
- CLOSED PR exists, no OPEN PR, and no MERGED PR anywhere on the branch: `NEEDS_HUMAN`, because the PR was closed without merge and the run never silently reopens human-rejected work.

### Explain stop

`--explain` stops after classification. It prints the selected spec, the classified stage, the routing row and gate section it came from, the review backend, task counts, consulted status fields, the resolved zero-task route as would-record (with its signal), the PR probe result if any, skipped candidates, and any would-clear ledger entries. It additionally prints `chain=<off|on>` from `CHAIN_ENABLED` and, only when on, a precondition-checked `would-chain=`: a classified `qa` stage prints `would-chain=make-pr (conditional on a fresh terminal qa_outcome)`, a conditional, never a promise, since explain dispatches nothing; any other classified stage prints `would-chain=none (stage <x> heads no pair)`. It writes no ledger (the ledger file is never created or modified on an explain run), records no route, checks out no branch, and dispatches nothing. Before this terminal, remove the root config snapshot so an explain run leaves no persistent scratch state: `rm -f "${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json"`.

```text
PILOT_VERDICT=NO_WORK spec=<id> stage=<stage> reason="dry-run: classification only, nothing dispatched"
```

Done when: exactly one stage from `{plan, plan-review, work, qa, make-pr}` is named, or the hop has resolved to a `NEEDS_HUMAN` / `DEFERRED_TO_LAND` terminal, with the routing row, the gate section, the consulted status fields, task counts, and any PR-probe result echoed.

## Phase 3 - Branch resolution matrix

The run owns branch resolution and runs it before every hop. Reuse `BRANCH_NAME` from Phase 2 (resolve it here when classification never reached the all-done branch):

```bash
[[ -n "${BRANCH_NAME:-}" ]] || BRANCH_NAME="$(printf '%s\n' "$SPEC_JSON" | jq -r '.branch_name // empty')"
if [[ -n "$BRANCH_NAME" ]] && git -C "$REPO_ROOT" rev-parse --verify --quiet "$BRANCH_NAME" >/dev/null; then
  BRANCH_EXISTS=1
else
  BRANCH_EXISTS=0
fi
```

Matrix:

| State | Action |
|---|---|
| branch exists and stage is `work` | `git checkout <branch_name>`, dispatch work with `--branch=current` |
| branch absent and stage is the first `work` hop | dispatch work with `--branch=new`; under autonomy work names it exactly the spec's `branch_name`, so later hops find it |
| stage is `qa` and branch exists | `git checkout <branch_name>`; QA drives the running app against this branch's build (never the default branch; the app under test is the spec's build). After checkout `HEAD` equals the branch head, so the Phase 5 post-dispatch freshness verify uses `HEAD`. |
| stage is `qa` and branch absent | `NEEDS_HUMAN`, reason `all tasks done but spec branch missing — inconsistent state` (all-done with no branch is the same inconsistency as the make-pr row; QA never silently skips) |
| stage is `make-pr` and branch exists | `git checkout <branch_name>`; make-pr auto-detects the spec from the branch |
| stage is `make-pr` and branch absent | `NEEDS_HUMAN`, reason `all tasks done but spec branch missing — inconsistent state` |
| stage is `plan` or `plan-review` | Probe the current branch for an OPEN PR: `gh pr list --head "$(git branch --show-current)" --state open` (an empty branch name, detached HEAD, counts as probe failure, not as an open PR). No open PR (including a fresh worktree branch or the default branch itself): stay on the current branch and dispatch. An open PR exists: `git checkout` the default branch (local `main`, else `master`); if that checkout fails (e.g. another worktree holds it), `NEEDS_HUMAN` naming the branch and the reason. Probe failure (gh unavailable or errors): attempt the default-branch checkout; if it fails, `NEEDS_HUMAN` (fail-safe: never plan onto a branch whose PR status is unknown). |

The invariant is that planning state is never written onto a branch with an open PR; the open-PR probe enforces it, wherever the run runs (shared checkout or secondary worktree). It guards the open-PR hazard only; a branch carrying another spec's not-yet-PR'd work is not detected. A long-horizon run may cross from a plan hop on the default branch to a work hop on the spec branch; each hop's row handles it.

If an attempted checkout fails (any attempted checkout in the matrix, including the open-PR fallback to the default branch), stop with `NEEDS_HUMAN`; do not dispatch and do not strike.

Done when: the worktree is on the branch this stage's matrix row names (or the plan/plan-review stay-put outcome applied), or the run has already terminated `NEEDS_HUMAN` without dispatching.

## Phase 4 - DISPATCH exactly one sub-skill (workflow.md Step 3)

Record the pre-dispatch evidence snapshot before invoking the stage skill:

- `plan`: task count from `$FLOWCTL tasks --spec <id> --json`.
- `plan-review`: `plan_review_status` from `$FLOWCTL show <id> --json`.
- `work`: per-task id/status list, spec status, and `completion_review_status`.
- `qa`: absence of a fresh `qa_verdict` receipt (`QA_FRESH=0`), already proven by the classify-time freshness probe; the post-dispatch verify re-reads the receipt against the **code head** (HEAD peeled past the qa-verdict bookkeeping commit).
- `make-pr`: no OPEN PR for the branch, already proven by the all-done probe.

**Backlog mode: guard the dispatch (invariant #1).** When `PILOT_AUTONOMY=backlog`, set `DISPATCH_TARGET` to the stage's slash command and call the allowlist assert immediately before invoking it; a forbidden merge/land/resolve target hard-exits `NEEDS_HUMAN` rather than dispatching:

```bash
if [ "${PILOT_AUTONOMY:-ready}" = "backlog" ]; then
  DISPATCH_TARGET="/flow-next:$STAGE"      # e.g. /flow-next:work
  assert_allowed_dispatch "$DISPATCH_TARGET"
fi
```

workflow.md Step 3 runs here. What this run adds is `mode:autonomous` (and `FLOW_AUTONOMOUS=1` semantics for any process-level work the stage starts) plus the passthroughs on each invocation:

- `plan`: `$flow-next-plan <spec-id> mode:autonomous --research=<grep|rp> --depth=<level> --review=<backend>`
- `plan-review`: `$flow-next-plan-review <spec-id> --review=<backend>`
- `work`: `$flow-next-work <spec-id> mode:autonomous --branch=<current|new> --review=<backend>`; when classification took the direct route for a zero-task spec, append `--no-plan`. For an admitted direct-owner resume, append the owner ID and prior-run-ended evidence reference as dispatch context, retaining the spec target and `SPEC_MODE`. Work re-anchors the owner without minting or automatic plan-review; additional or intentional tasks follow the planned route.
- `qa`: `$flow-next-qa <spec-id> mode:autonomous` (the token suppresses the QA skill's prompts so the loop cannot hang on a question)
- `make-pr`: `$flow-next-make-pr <spec-id> mode:autonomous`

If a sub-skill crashes, asks for judgment under autonomy, or reports ambiguity that needs a person, stop with `NEEDS_HUMAN`. Do not cleanup, reset claims, or record a strike.

Done when: exactly one stage skill has been invoked and has returned; a hop that dispatched a second stage has broken the contract, with one gated exception: under `--tick` with `pipeline.chainStages` on, Phase 5's Chained stage dispatches `make-pr` after this tick's `qa` stage verified `QA_ADVANCED=true`; any other second dispatch still breaks it.

## Phase 5 - VERIFY + evidence echo (workflow.md Step 4)

workflow.md Step 4 runs here. What this run adds is the evidence echo a transcript-only driver validates from, the receipt and PR re-reads that decide `advanced` for each stage, and the post-hop dirty-tree guard. One evidence block and one stage-outcome line per hop stay in the transcript for the whole run.

**Stage-outcome line.** Every evidence echo additionally carries the one `stage:` line `references/gate-selection.md` (Receipts) defines for the stage this hop dispatched; a QA skip under `pipeline.qa=auto` is recorded at the classify-time skip. Append `(model: <what actually ran>)` only when this hop knows what executed the stage (a named subagent model, a bridged CLI invoked with an explicit model, a review backend that reported one). Record what ran, never what the routing block preferred, and omit the annotation when the harness did not expose it rather than writing `auto` / `default` / `unknown`. Timestamps only where this hop knows them; token/cost telemetry is out of scope (host-side data flowctl cannot observe).

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

For `qa`, advancement is judged from the **post-dispatch `qa_verdict` receipt**, observed state, never the QA skill's narration. Read the receipt's `qa_outcome` field, never the Ralph-guard `verdict` projection (the QA skill projects `BLOCKED->verdict=NEEDS_WORK`, so a hop that read `verdict` conflated "couldn't verify" with "found problems" and has broken this).

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

**The QA skill commits its own handoff** (the `qa_verdict` receipt plus the exact bug-memory it filed) in autonomous mode (qa §6.3b), so the receipt is already on the branch and rides the eventual make-pr push. **The run adds no commit of its own here**: the agent that wrote the files commits them precisely, so the run never sweeps the tree or guesses paths.

A missing/stale receipt (`QA_ADVANCED=false`) is the healthy-no-advance path (Phase 6 strike), NOT a crash: the QA skill ran but produced no fresh verdict (e.g. it errored before writing). **Don't-thrash + non-fatal:** the freshness gate prevents re-classifying `qa` once a fresh receipt exists, so the same spec is bounded to one qa pass per branch-head; the interactive work/qa re-pass (out of scope here; autonomous surfaces and proceeds) is bounded by the existing strike/auto-block reflexes (2 strikes unready the spec). `BLOCKED` from a missing app is a fresh terminal outcome, never a failed loop.

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

### Chained stage (`pipeline.chainStages`, `--tick` only)

The chain table is closed: one row, one switch, no per-pair knobs, and it is entered only under `--tick` (`CHAIN_ENABLED` is never set in long-horizon mode, where the next hop already runs `make-pr`):

| Completed stage | Chained stage | Entered only when |
|---|---|---|
| `qa` | `make-pr` | `CHAIN_ENABLED=1` (Phase 2, which requires `AUTO_TICK=1`) **and** this tick's qa verify decided `QA_ADVANCED=true`: any fresh terminal `qa_outcome` (SHIP, NEEDS_WORK, NA, BLOCKED), exactly the set the unchained next tick would make-pr on |

`plan` heads no row: the plan dispatch already carries `--review=<backend>` and the plan skill's own Step 7 runs its review fix loop to SHIP inside that dispatch, so a successful plan tick already classifies `work` next; a second review of the unchanged plan would be a paid no-op (or a `NOT_RETRYABLE` terminal). `work` heads no row and is never a target: a NEEDS_WORK review, an unfinished implementation, and the completion gate are human territory. `make-pr` heads no row (it is the terminus). A missing/stale receipt (`QA_ADVANCED=false`) never chains; it takes the healthy-no-advance strike path with `stage=qa`.

When the row is entered, run the chained `make-pr` exactly as the standalone stage runs it; reference those phases, never restate them:

1. Phase 3 branch row for `make-pr` with the branch existing: the qa checkout already put the worktree on `BRANCH_NAME`, so there is no second checkout.
2. Phase 4 pre-dispatch evidence for `make-pr`: no OPEN PR, already proven by this tick's all-done probe. In backlog mode guard the dispatch first: `DISPATCH_TARGET="/flow-next:make-pr"; assert_allowed_dispatch "$DISPATCH_TARGET"` (`/flow-next:make-pr` is on the allowlist; the assert still runs before every dispatch).
3. The Phase 4 dispatch line: `/flow-next:make-pr <spec-id> mode:autonomous`. The PR stays draft under autonomy; the run still never invokes land or merges.
4. The Phase 5 `make-pr` verify above: the same gh open-PR probe, a second `Evidence:` block (`stage=make-pr`), and its own `stage:` outcome line. The qa stage's evidence block and outcome line stay in the transcript as already echoed; one evidence block and one `stage:` line per dispatched stage.
5. Phase 6 under `stage=qa+make-pr`: the qa `ADVANCED` ledger clear first, then make-pr's own clear or strike with `STAGE=make-pr`. A dirty non-`.flow/` tree or a verify-probe failure (`PR_VERIFY_FAILED=1`) after the chained dispatch is crash-class `NEEDS_HUMAN`, no strike, as for any stage.

Nothing else chains. `CHAIN_ENABLED=0` (the default, and always in long-horizon mode) leaves this subsection unentered.

Done when: every dispatched stage's before/after evidence block and `stage:` outcome line are in the transcript, each `advanced` was decided from re-read state rather than sub-skill narration, and the post-hop dirty-tree guard passed.

## Phase 3.5 - ASK (backlog mode only, non-workable subjects)

**Active only when `PILOT_AUTONOMY=backlog` AND Phase 1.6 routed the subject to `ask`** (ready-but-thin / needs-spec / needs-human / force-gated). Execute [references/backlog-mode.md](references/backlog-mode.md) Phase 3, the async question valve. **Never asks interactively** (`plain-text numbered prompt` is forbidden on the run path; the human answers later via the spec or the tracker).

**Enforce invariant #2 inline before any spec-side write.** A spec-backed subject writes `## Open Questions`; a tracker-only subject (empty/absent `SPEC_PATH`) must hard-exit rather than author a spec stub. Call the assert with the resolved paths, then guard the dispatch (invariant #1):

```bash
# Spec-backed: SPEC_PATH points at an EXISTING spec file -> the assert passes and the op writes the
# `## Open Questions` anchor. Tracker-only: SPEC_PATH is empty -> the assert hard-exits, so the op is
# invoked WITHOUT touching any spec (the question lives in the tracker comment alone). Run the assert
# ONLY when a spec-side write is intended (HAS_SPEC=1); a tracker-only subject skips it and parks in
# the tracker.
[ "${HAS_SPEC:-0}" = "1" ] && assert_spec_write_allowed "$SUBJECT_ID" "$SPEC_PATH"
DISPATCH_TARGET="/flow-next:tracker-sync question"; assert_allowed_dispatch "$DISPATCH_TARGET"
```

The question is then posted through tracker-sync's inline `question` wrapper. The skill owns semantic question authoring and structured recovery; flowctl owns deterministic comment transport, marker dedup, and normalized answer readback. Backlog mode invokes the wrapper and never re-implements it:

```text
/flow-next:tracker-sync question <SUBJECT_ID> mode:autonomous     # <SUBJECT_ID> = spec id (spec-backed) OR the list-open issue.identifier (tracker-only: the display handle, NOT the global id; GitLab needs the <project>#<iid> it carries to post …/issues/:iid/notes)
```

Where the question parks (spec-backed `## Open Questions` anchor plus mirrored tracker comment, versus tracker-only comment ALONE, never a spec stub), the idempotent anchor-id dedup, and the spec-first floor / no-transport `NEEDS_HUMAN` degradation are single-sourced in [references/backlog-mode.md](references/backlog-mode.md) Phase 3; execute them as written there.

```text
PILOT_VERDICT=ASKED spec=<id> stage=ask reason="parked behind <n> open question(s): <one line>"
```

(`spec=<id>` is the spec id for a spec-backed subject, else the tracker id for a tracker-only subject.)

## Phase 6 - REPORT + strikes ledger

On `ADVANCED`, clear the selected spec's ledger entry if present and write the ledger atomically with `jq` plus `mv`:

```bash
mkdir -p "$LEDGER_DIR"
[ -s "$LEDGER" ] || echo '{}' > "$LEDGER"
tmp="$LEDGER.tmp.$$"
jq --arg spec "$SELECTED_SPEC" 'del(.[$spec])' "$LEDGER" > "$tmp" && mv "$tmp" "$LEDGER"
```

Then, when the hop loop continues (long-horizon mode, an `ADVANCED` stage other than `make-pr`), return to Phase 2.

When the run ends, print the terminal line. `stage=` names every dispatched stage in order joined by `+`; the reason names the last hop's outcome:

```text
PILOT_VERDICT=ADVANCED spec=<id> stage=<stage> reason="<what advanced>"
```

For a `qa` stage the reason names the fresh `qa_outcome` so a transcript-only driver sees the result without re-reading the receipt, e.g. `reason="qa pass: qa_outcome=NEEDS_WORK — findings surfaced on draft PR"` or `reason="qa pass: qa_outcome=BLOCKED — no local app reachable, advancing"`. Only a *missing/stale* receipt routes to the healthy-no-advance strike below.

For a run that dispatched several stages (a long-horizon run, or the `--tick` chain) the ledger writes are sequential within the single-threaded run: each stage's `ADVANCED` clear completes (atomic `jq` plus `mv`) before the next stage records its own clear or strike under its own `STAGE`; there is no clear-versus-strike race. The verdict is the last dispatched stage's verdict; `stage=` names every dispatched stage in order joined by `+`; the reason names the last outcome, and for the chained tick both outcomes, the fresh `qa_outcome` and the PR URL or its absence:

```text
PILOT_VERDICT=ADVANCED spec=<id> stage=work+qa+make-pr reason="make-pr: open PR <url>"
PILOT_VERDICT=ADVANCED spec=<id> stage=qa+make-pr reason="qa pass: qa_outcome=<outcome>; make-pr: open PR <url>"
PILOT_VERDICT=BLOCKED spec=<id> stage=qa+make-pr reason="no advancement (strike 1/2): qa pass: qa_outcome=<outcome>; make-pr: no open PR for <branch>"
```

A `make-pr` that yields no open PR strikes under `make-pr` exactly as a standalone tick would; a driver grepping `PILOT_VERDICT=ADVANCED` keeps working.

On healthy-but-no-advance, record a strike with count, stage, reason, and timestamp:

```bash
mkdir -p "$LEDGER_DIR"
[ -s "$LEDGER" ] || echo '{}' > "$LEDGER"
tmp="$LEDGER.tmp.$$"
jq --arg spec "$SELECTED_SPEC" --arg stage "$STAGE" --arg reason "$NO_ADVANCE_REASON" --arg ts "$TODAY" '
  .[$spec].count = ((.[$spec].count // 0) + 1)
  | .[$spec].stage = $stage
  | .[$spec].reason = $reason
  | .[$spec].ts = $ts
' "$LEDGER" > "$tmp" && mv "$tmp" "$LEDGER"
STRIKE_COUNT="$(jq -r --arg spec "$SELECTED_SPEC" '.[$spec].count' "$LEDGER")"
```

If `STRIKE_COUNT` is `1`, leave the spec ready, end the run, and print:

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="no advancement (strike 1/2): <why>"
```

If `STRIKE_COUNT` is `2`, unready the spec, keep the ledger reason, and print:

```bash
$FLOWCTL spec unready "$SELECTED_SPEC"
```

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="no advancement (strike 2/2, spec unreadied): <why>; clear with: flowctl pilot strikes clear <id>"
```

The recovery clause is part of the reason string, not a separate line: a strikeout is the one terminal a human must undo by hand, and on a repo with `tracker.readyState` armed the board cannot undo it (Phase 1 item 3), so the transcript-only driver or human reading this verdict gets the exact command. Keep it last in the reason, after `<why>`.

### Backlog-mode dep-wait `BLOCKED` terminal (distinct from the strike path)

**Active only when `PILOT_AUTONOMY=backlog` AND Phase 1.6 routed the subject to `dep-unsatisfied`.** This is a SEPARATE `BLOCKED` terminal from the strike-based one above: it is a clean **dep-wait surface** (the selected, signalled item has an acyclic-but-unsatisfied blocker, Phase 1.6 / Phase 1f), **not** a no-advancement failure. It records **no strike** (the spec is healthy; it is simply waiting on a blocker the topo-sort offers first on a later run), does **not** unready the spec, and writes the `blocked` decision-log row (the dep-wait, not a strike). `<dep>` is the unsatisfied blocker id (flow `blockedBy` edge or tracker relation); name the first when several:

```bash
# No ledger write; a dep wait is healthy, not a strike. STAGE is the stage the
# item would advance to once unblocked (or '-'); $SUBJECT_ID is spec-backed or a
# tracker key. The `blocked` action distinguishes the dep wait from the strike path.
$FLOWCTL pilot-log append --id "$SUBJECT_ID" --action blocked --stage "${STAGE:--}" ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"}
```

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="dep wait — blocked by <dep> (not yet done); topo-sort offers the blocker first next tick"
```

(A circular/unsatisfiable dep does NOT reach here; Phase 1e routes it to `ASKED` instead. This terminal is for the plain acyclic dep wait only.)

Crash-class outcomes are `NEEDS_HUMAN`: sub-skill crash, dirty non-`.flow/` tree after dispatch, gh probe failure in the all-done branch or at the make-pr verify (`PR_VERIFY_FAILED=1`), branch inconsistency, closed-without-merge PR (with no merged PR on the branch), merged-PR-with-nothing-new-beyond-its-head, stale in-progress-only claim, a review that exits `NOT_RETRYABLE`, or autonomy ambiguity. Leave state untouched and record no strike:

```text
PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=<stage> reason="<one line>"
```

An all-done spec with an **open** PR is *not* crash-class; it is the benign `DEFERRED_TO_LAND` terminal below (land owns the merge). Only the closed-unmerged-with-no-merged-PR, missing-branch, and merged-with-nothing-new (branch head equals the newest merged PR head) all-done states are `NEEDS_HUMAN`; merged plus commits beyond that head classifies `make-pr` even when older closed PRs share the branch. An all-done spec with **no** PR is never terminal at all; it classifies `qa` or `make-pr` and dispatches.

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

### Backlog-mode decision log - one row per dispatched stage, at the resolving terminal

**Active only when `PILOT_AUTONOMY=backlog`.** Every backlog run that selected a subject appends exactly **one** decision-log row per dispatched stage (one per hop, two on a chained `qa+make-pr` tick), each with its own `--stage`, keyed to the verdict grammar action, at its resolving terminal. The row co-occurs with the state-changing terminal; a live `TRIAGED` is never a bare no-op, so the logged action is always a terminal action. Stored under `.flow/pilot-runs/` (a sync-runs-style dir, NOT a ralph-guard `receipts/` path), auto-gitignored:

```bash
# ACTION in {advanced, asked, blocked, needs-human}  (mapped from the terminal verdict)
#   ADVANCED  -> advanced   · ASKED -> asked   · BLOCKED -> blocked   · NEEDS_HUMAN -> needs-human
# STAGE is the pipeline stage advanced/blocked-at, or 'ask' for ASKED, or '-' when none.
# COST_TOKENS is host-reported (this run's token cost); omit the flag when unavailable.
$FLOWCTL pilot-log append --id "$SUBJECT_ID" --action "$ACTION" --stage "${STAGE:--}" ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"}

# A run that dispatched several stages appends one row per stage, in dispatch order.
# Every intermediate row is `advanced` (the loop continued only from ADVANCED) and
# carries NO cost; the last row carries the run's terminal action and the
# whole-run cost ONCE. Each append mints its own row id, so a multi-hop run
# reads as several rows in the log, never as a doubled cost.
# $FLOWCTL pilot-log append --id "$SUBJECT_ID" --action advanced --stage qa
# $FLOWCTL pilot-log append --id "$SUBJECT_ID" --action "$ACTION" --stage make-pr ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"}
```

- **`--id`** takes the spec id (spec-backed) OR the bare tracker key (tracker-only); flowctl safe-filename-normalizes it.
- **`--action`** is the frozen enum `triaged|advanced|asked|blocked|needs-human`. A **live** run logs only terminal actions (`advanced`/`asked`/`blocked`/`needs-human`); `triaged` is for a diagnostic/explain inspection only, matching the `TRIAGED` diagnostic-only verdict.
- **`--cost-tokens`** is host-reported by the skill (flowctl only stores the row; it never measures cost). Omit the flag when the host cannot report it.

A `NO_WORK` / `DEFERRED_TO_LAND` run selected no subject, so it writes **no** row (there is nothing to log against). An `--explain` run writes no row (classification/inspection only). Exactly one row per dispatched stage on an acting backlog run.

**The dep-wait `BLOCKED` terminal above already emits its own `--action blocked` row inline**; that is its single decision-log row, so this generic block adds none for that path. It covers the other resolving terminals (`advanced` / `asked` / `needs-human`) and the strike-based `BLOCKED`. Whichever terminal resolves a dispatched stage writes exactly **one** row for it; a second row for the same stage, or a dispatched stage with no row, has broken this.

Done when: the ledger reflects this hop (cleared on `ADVANCED`, incremented on healthy-no-advance, untouched on crash-class), one decision-log row per dispatched stage was appended, and either the next hop has started or the terminal verdict line is printed.

The `PILOT_VERDICT` line is always the last line of the run's output. Print nothing after it.
