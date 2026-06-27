# /flow-next:pilot workflow

Execute these phases in order. One invocation advances at most one selected spec by one pipeline stage and ends with the terminal verdict line.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

Shared shell context for the workflow:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODAY="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

`jq`, `git`, and `gh` must be on PATH when classification reaches the all-done PR branch. `PILOT_SPEC`, `PILOT_DRY_RUN`, `PILOT_REVIEW`, `PILOT_RESEARCH`, and `PILOT_DEPTH` come from SKILL.md Mode Detection.

## Phase 0 — Guards

Hard-stop when pilot is invoked under the Ralph harness. Emit the parseable terminal failure and dispatch nothing:

```bash
if [[ -n "${FLOW_RALPH:-}" || -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
 echo "Ralph and pilot are alternative drivers — never nest them" >&2
 echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="nested under Ralph harness (FLOW_RALPH/REVIEW_RECEIPT_PATH set) — refuse to run"'
 exit 1
fi
```

Refuse a dirty non-`.flow/` tree at tick start. Leave state untouched for diagnosis:

```bash
if git -C "$REPO_ROOT" status --porcelain | grep -v '^.. \.flow/' >/dev/null; then
 echo "Evidence: dirty non-.flow working tree at tick start"
 git -C "$REPO_ROOT" status --porcelain | grep -v '^.. \.flow/' || true
 echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="dirty working tree at tick start"'
 exit 0
fi
```

Resolve the strikes ledger after both hard guards — READ-ONLY here (a missing file reads as `{}`; nothing is created or written until a write site in Phase 1 or Phase 6, so `--dry-run` leaves the filesystem untouched). It lives under the git common dir so it is shared across worktrees and cannot be swept into commits by `git add -A`:

```bash
LEDGER_DIR="$(git -C "$REPO_ROOT" rev-parse --git-common-dir)/flow-next"
LEDGER="$LEDGER_DIR/pilot-strikes.json"
LEDGER_JSON="$(cat "$LEDGER" 2>/dev/null || echo '{}')"
```

Ledger schema: `{"<spec-id>": {"count": <n>, "stage": "<stage>", "reason": "<one line>", "ts": "<iso8601>"}}`. It is skill-owned scratch; no flowctl plumbing. Every write site runs `mkdir -p "$LEDGER_DIR"` plus `[ -s "$LEDGER" ] || echo '{}' > "$LEDGER"` first, then writes atomically with `jq` plus `mv`.

## Phase 0.5 — Autonomy mode + backlog safety invariants (R1, R6)

`PILOT_AUTONOMY` was resolved in SKILL.md Mode Detection (strict scalar `pilot.autonomy == "backlog"`, or the `--backlog` / `--auto` override). **Everything backlog-specific — the autonomy export AND the safety-invariant helpers — lives inside a single `if [ "$PILOT_AUTONOMY" = backlog ]` branch**, so ready mode incurs **zero** side effects (no `FLOW_AUTONOMOUS` export, no helper definitions, no backlog-mode.md load):

```bash
if [ "${PILOT_AUTONOMY:-ready}" != "backlog" ]; then
 : # ready mode — Phases 1–6 run exactly as written; nothing below runs;
 # FLOW_AUTONOMOUS is NOT exported; backlog-mode.md is never read (R1).
else
 # backlog mode — everything below is scoped to THIS branch:

 # Export the autonomy marker so every sub-skill / tracker-sync op this tick runs
 # unattended (plain-text numbered prompt is never reached — R14). Load backlog-mode.md (the
 # agentic SELECT/TRIAGE/ASK workflow) now; Phase 1.5 / 1.6 / 3.5 execute it.
 export FLOW_AUTONOMOUS=1

 # Invariant #1 — never merge / never invoke land (R6). The ONLY skills a backlog
 # tick may invoke are the pipeline stages {plan, plan-review, work, qa, make-pr}
 # plus the tracker-sync surfacing/read ops {reconcile, list-open, list-relations,
 # question}. ALL FOUR tracker ops are read/surface-only — none merges, lands, or
 # resolves, so the never-merge guard is unaffected. `list-relations` is the
 # per-issue listIssueRelations READ that 1e needs for tracker dep edges. Called
 # inline immediately before EVERY dispatch (Phase 1.5 tracker ops, Phase 3.5 ask,
 # Phase 4 stage dispatch) with the about-to-run slash command.
 assert_allowed_dispatch() { # $1 = the slash command about to be invoked
 case "$1" in
 /flow-next:plan|/flow-next:plan-review|/flow-next:work|/flow-next:qa|/flow-next:make-pr) return 0 ;;
 "/flow-next:tracker-sync reconcile"*|"/flow-next:tracker-sync list-open"*|"/flow-next:tracker-sync list-relations"*|"/flow-next:tracker-sync question"*) return 0 ;;
 *)
 echo "Evidence: backlog mode attempted a forbidden dispatch ($1)"
 echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="backlog mode dispatch allowlist — never merges/lands/resolves (R6)"'
 exit 1 ;;
 esac
 }

 # Invariant #2 — never author a spec. The ask stage may write spec-side ONLY when
 # the spec file ALREADY exists (fill an obvious blank in an existing spec). A
 # tracker-only item has NO spec — its question parks in the tracker comment ALONE.
 # Called inline in Phase 3.5 before any spec-side write.
 assert_spec_write_allowed() { # $1 = SUBJECT_ID, $2 = SPEC_PATH (empty for tracker-only)
 if [ -z "$2" ] || [ ! -f "$2" ]; then
 echo "Evidence: backlog mode attempted to author a spec for a specless item ($1)"
 echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=ask reason="backlog mode never authors specs — surfaced as needs capture/interview gap (R3/R4)"'
 exit 1
 fi
 }
fi
```

**Ready mode is byte-for-byte unchanged** — the gate-off branch is a bare `:` no-op: no backlog block below runs, `references/backlog-mode.md` is never loaded, `FLOW_AUTONOMOUS` is never exported, and the verdict grammar/stage set match today's pilot exactly (R1).

### Backlog safety invariants — ENFORCING guards, not prose (R6)

The four invariants are **hard bash branches enforced inline at their real site** (an executing agent — and a reviewer — reads the snippet as authoritative). Each short-circuits a forbidden action with a parseable terminal line; none is advisory prose. The two assert helpers above are defined only in the backlog branch and called inline at the dispatch and ask sites; invariants #3/#4 are enforced where selection happens (Phase 1.5):

- **Invariant #1 (never merge/land)** is enforced by `assert_allowed_dispatch "$DISPATCH_TARGET"` called inline immediately before **every** dispatch — the Phase 1.5 tracker-sync ops, the Phase 3.5 `question` op, and the Phase 4 stage dispatch. A `/flow-next:land`, `gh pr merge`, or `/flow-next:resolve-pr` never reaches the allowlist's `return 0`.
- **Invariant #2 (never author a spec)** is enforced by `assert_spec_write_allowed "$SUBJECT_ID" "$SPEC_PATH"` called inline in Phase 3.5 **before any spec-side write** — a tracker-only (empty/absent `SPEC_PATH`) subject hard-exits rather than creating a spec stub.
- **Invariant #3 (single-tick)** is enforced in Phase 1.5 by the `SELECTED_COUNT` assertion — selection picks exactly **one** `SUBJECT_ID`; a `SELECTED_COUNT != 1` is a hard error, and there is no `for item in candidates` advance/park loop anywhere downstream.
- **Invariant #4 (dep cycle/deadlock → surface)** is enforced in Phase 1.5e by the `DEP_DEADLOCK` branch — an un-placeable circular/unsatisfiable dep routes to `ASKED` / `BLOCKED` with a terminal verdict, never falls through to be re-picked next tick.

## Phase 1 — SELECT (two-pass)

**Ready mode only.** This two-pass selection runs when `PILOT_AUTONOMY=ready` (the default). In **backlog mode** it is REPLACED by Phase 1.5's wide SELECT (which reuses the same dependency / claim / re-bless checks but widens the candidate set and acts on the skip pile instead of dropping it to `NO_WORK`). Skip directly to Phase 1.5 when `PILOT_AUTONOMY=backlog`.

Pass 1 enumerates minimal candidates:

```bash
SPECS_JSON="$($FLOWCTL specs --json)"
```

Candidate predicate for pass 1:

- `status == "open"`.
- ready flag is set.
- stable id order.
- if `--spec <id>` was provided, the candidate list is exactly that spec and it still must pass the predicate.

Echo the pass-1 counts: total specs, open specs, ready specs, and scope-lock target if present.

Pass 2 loads full spec JSON for each candidate:

```bash
SPEC_JSON="$($FLOWCTL show "$candidate" --json)"
TASKS_JSON="$($FLOWCTL tasks --spec "$candidate" --json)"
```

Apply the full predicate:

1. Dependencies: every `depends_on_epics[]` value is satisfied iff `$FLOWCTL show <dep> --json` reports `status == "done"`. Any unsatisfied dependency skips the candidate and records `deps unsatisfied: <ids>`.
2. Collision avoidance: no task may be `in_progress` and assigned to another actor. The minimal `tasks --spec` listing carries no `assignee` — for every task with `status == "in_progress"`, fetch `$FLOWCTL show <task-id> --json` and read its `assignee` field. Resolve this session's actor identity exactly as `flowctl.get_actor()` does: `$FLOW_ACTOR` env var, else `git config user.email`, else `git config user.name`, else `$USER`, else `unknown`. If resolution bottoms out at `unknown`, any non-empty assignee counts as another actor.
3. Strikes: a ledger entry with `count >= 2` normally means the spec was unreadied after failure, but a candidate that is ready again has been human re-blessed. Clear that ledger entry (write site: `mkdir -p "$LEDGER_DIR"`, seed if missing, then atomic `jq` plus `mv`) and treat the spec as fresh. Under `--dry-run`, do not write — report the entry as would-clear in the classification report instead.
4. No gh here. PR state belongs exclusively to the all-done classification branch.

The first candidate passing everything becomes `SELECTED_SPEC`. If none pass, echo a compact skip table with counts by reason and stop:

```text
PILOT_VERDICT=NO_WORK spec=- stage=- reason="no ready spec with satisfied deps"
```

## Phase 1.5 — SELECT (wide, backlog mode only) — R2, R3, R7, R16

**Active only when `PILOT_AUTONOMY=backlog`.** Execute the SELECT workflow in [references/backlog-mode.md](references/backlog-mode.md) Phase 1 — it is the agentic floor scheduler, loaded only in this mode. The mechanics there are authoritative; the binding flow is:

**`--dry-run` is dispatch-free.** A `--dry-run` backlog tick is inspection-only: it MUST dispatch nothing and mutate nothing (no readiness projection, no receipts). So when `PILOT_DRY_RUN=1`, **skip the tracker-sync `reconcile` (1a) and `list-open` (1c) dispatches entirely** and select from the **flow-side `ready --all` facts alone** — then Phase 1.6 classifies and the tick stops with the diagnostic `TRIAGED` line (no `ask`, no pilot-log row). The gate below wraps every Phase 1.5 dispatch:

```bash
DRY="${PILOT_DRY_RUN:-0}" # 1 ⇒ inspection-only: no tracker-sync dispatch, flow-side facts only
```

1. **1a — pull-before-scan (R16).** Run an unattended tracker-sync reconcile FIRST so readiness from the tracker is fresh this tick, then scan. **Skipped under `--dry-run`** (dispatch-free). Otherwise guard the dispatch (invariant #1), then dispatch the tracker-sync `reconcile` op under the autonomy gate:

 ```bash
 if [ "$DRY" = "0" ]; then
 DISPATCH_TARGET="/flow-next:tracker-sync reconcile"; assert_allowed_dispatch "$DISPATCH_TARGET"
 # → dispatch: /flow-next:tracker-sync reconcile mode:autonomous (FLOW_AUTONOMOUS=1; no-op when the bridge is inactive)
 fi
 ```

 A no-op (inactive bridge) is fine — selection proceeds on the flow facts alone (R17 spec-first floor). It never blocks and never prompts (R14). Under `--dry-run` the reconcile is skipped, so the dry-run readiness read is whatever `ready --all` already reflects locally — acceptable for an inspection-only tick.

2. **1b — scan the flow side (facts).** `READY_ALL_JSON="$($FLOWCTL ready --all --json)"` → the flow-side open specs with deterministic eligibility facts `{id, ready, readySignal, blockedBy, hasSpec}` (R8). flowctl returns **no** `triageClass` — the class is the agent's read in Phase 3.5.

3. **1c — union the tracker side (`list-open`).** **Skipped under `--dry-run`** (dispatch-free — a dry-run tick selects from the flow-side `ready --all` facts alone). Otherwise guard the dispatch (invariant #1), then union in the tracker-only promoted issues (no flow spec) via the tracker-sync `list-open` op:

 ```bash
 if [ "$DRY" = "0" ]; then
 DISPATCH_TARGET="/flow-next:tracker-sync list-open"; assert_allowed_dispatch "$DISPATCH_TARGET"
 # → dispatch: /flow-next:tracker-sync list-open mode:autonomous (no-ops when tracker.readyState unset → flow-ready specs only)
 fi
 ```

 De-dup linked issues (they already appear on the flow side) by tracker id / `flow:<id>` label. Under `--dry-run` the candidate set is the flow specs (1b) only — no tracker-only items are unioned in.

4. **1d — skip parked subjects (R7/R15).** Skip any candidate carrying a `status=open` parked question — spec-backed: a `<!-- flow-next:question id=… status=open -->` anchor in `## Open Questions`; tracker-only: a `flow-next:question id=… status=open` comment with no matching `<!-- flow-next:answer id=… -->`. An anchor flipped to `status=answered` is no longer parked — it re-enters and is re-triaged this tick.

5. **1e — dep-order the survivors.** Feed the flow `blockedBy` edges + the per-issue tracker `relation[]` edges into the **flow-next-deps jq topo-sort** — reuse it, build no new graph engine. The tracker relation edges come from the per-issue `listIssueRelations` READ, dispatched via tracker-sync's `list-relations` op. Guard it (invariant #1) before dispatching — it is on the allowlist (a READ, never a merge):

 ```bash
 if [ "$DRY" = "0" ]; then
 # For each TRACKER candidate, read its relations to add the tracker dep edges.
 DISPATCH_TARGET="/flow-next:tracker-sync list-relations"; assert_allowed_dispatch "$DISPATCH_TARGET"
 # → dispatch per tracker issue: /flow-next:tracker-sync list-relations <tracker-id> mode:autonomous
 # (the listIssueRelations read; no-op/empty when the bridge is inactive or the issue has no relations)
 fi
 ```

 (Under `--dry-run` there are no tracker candidates — 1c was skipped — so 1e uses the flow `blockedBy` edges only and issues no tracker read; the guarded dispatch above is skipped.) **Invariant #4 — a cycle/deadlock is surfaced, never spun on.** When the topo-sort cannot place the chosen candidate because its dep chain is circular or a dep is itself parked/unsatisfiable, set `DEP_DEADLOCK=1` and route it to a state-changing terminal — never fall through to re-pick it next tick:

 ```bash
 if [ "${DEP_DEADLOCK:-0}" = "1" ]; then
 # The unresolvable dependency is surfaced as an async question (Phase 3.5 ask → ASKED).
 # (A plain unsatisfied-but-acyclic dep is NOT a deadlock — it routes to BLOCKED in Phase 1.6.)
 SUBJECT_ID="$DEADLOCK_SUBJECT_ID"; HAS_SPEC="$DEADLOCK_HAS_SPEC"; SPEC_PATH="$DEADLOCK_SPEC_PATH"
 ASK_REASON="unresolvable/circular dependency — $DEADLOCK_DETAIL"
 # → fall into Phase 3.5 ASK (terminal ASKED). Selection terminates this tick.
 fi
 ```

6. **1f — pick the top actionable item.** The first dep-ordered candidate that (a) carries an explicit readiness signal and (b) is not parked becomes `SUBJECT_ID` — the one item to triage in Phase 1.6. **A signalled item is selectable even when a dependency is unsatisfied** (it routes to `BLOCKED` in Phase 1.6, surfacing the dep wait — never dropped to `NO_WORK`). Only unsignalled items (never in the pool) and parked-unanswered ones (1d) are excluded.

7. **1g — apply pilot's ready-mode claim / collision / re-bless checks to the picked candidate (R2).** Backlog SELECT **reuses the SAME checks as Phase 1 Pass 2** — it does not skip them. Phase 1.6 CLASSIFY (and the downstream `NEEDS_HUMAN` stale-claim row) **assumes other-actor `in_progress` claims were already skipped at SELECT**, so they MUST be applied here, before triage. For a **spec-backed** `SUBJECT_ID` (a tracker-only item has no flow tasks, so this step is a no-op for it):

 - **Collision avoidance (Phase 1 Pass 2 rule 2, verbatim):** load `$FLOWCTL tasks --spec "$SUBJECT_ID" --json`; for every task with `status == "in_progress"`, fetch `$FLOWCTL show <task-id> --json` and read its `assignee`. Resolve this session's actor exactly as `flowctl.get_actor()` does (`$FLOW_ACTOR` → `git config user.email` → `git config user.name` → `$USER` → `unknown`; when it bottoms out at `unknown`, any non-empty assignee counts as another actor). **If a task is claimed by another actor, this candidate is NOT selectable** — drop it and advance to the next dep-ordered candidate (back to 1f), recording `claimed by other actor: <task-id>` in the skip table. Never select a spec another actor is mid-flight on.
 - **Strikes / re-bless (Phase 1 Pass 2 rule 3, verbatim):** a ledger entry with `count >= 2` normally means the spec was unreadied after failure; a candidate that is **ready again** has been human re-blessed — clear that ledger entry (write site: `mkdir -p "$LEDGER_DIR"`, seed if missing, then atomic `jq` plus `mv`) and treat the spec as fresh. Under `--dry-run`, do not write — report the entry as would-clear instead.
 - **No gh here** (Phase 1 Pass 2 rule 4) — PR state belongs exclusively to the all-done CLASSIFY branch.

 These are pilot's existing ready-mode SELECT checks — reuse them, do not reinvent. The dependency check is already covered by 1e (topo-sort) + the `dep-unsatisfied` triage class; 1g adds the claim + re-bless halves so the backlog candidate reaching Phase 1.6 has the same selection discipline a ready-mode candidate does.

**Invariant #3 — single-tick — is enforced here.** Selection sets exactly ONE `SUBJECT_ID`; there is no `for item in candidates` advance/park loop downstream. **Assign `SELECTED_SUBJECTS` to the chosen subject** (the single id 1f/1g settled on, or empty when the pool yielded none), resolve `SPEC_PATH` (the spec file path when spec-backed, else **empty** for a tracker-only item) and `HAS_SPEC`, then hard-assert the count:

```bash
# SELECTED_SUBJECTS = the chosen subject id — selection yields exactly one (or
# empty when no candidate survived 1f/1g). Assign it from SUBJECT_ID here so the
# single-tick guard below counts the REAL selection (an unset var would always
# count 0 and wrongly fall through to NO_WORK even after a subject was picked).
SELECTED_SUBJECTS="${SUBJECT_ID:-}"
SELECTED_COUNT="$(printf '%s\n' "$SELECTED_SUBJECTS" | grep -c . )"
if [ "$SELECTED_COUNT" -gt 1 ]; then
 echo "Evidence: backlog selection yielded $SELECTED_COUNT subjects — single-tick contract violated"
 echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="backlog single-tick — selection must pick exactly one item (R6 invariant #3)"'
 exit 1
fi
```

A `SELECTED_COUNT` of 0 (empty `SUBJECT_ID` — no candidate survived 1f/1g) falls through to the terminal split below (`NO_WORK`); exactly 1 proceeds to Phase 1.6.

Fall through to the existing terminal split **only when the pool is genuinely empty of a selectable candidate** — verbatim, backlog mode adds neither verdict:

- **`NO_WORK`** — no signalled, unparked candidate exists at all (and no dep wait to report):

 ```text
 PILOT_VERDICT=NO_WORK spec=- stage=- reason="no signalled, unparked backlog item"
 ```

- **`DEFERRED_TO_LAND`** — every all-done candidate has an open PR (the Phase 6 split, unchanged).

A signalled-but-dep-blocked candidate is **selectable**, so its presence yields `BLOCKED` (Phase 3.5), never `NO_WORK`.

## Phase 1.6 — TRIAGE the selected item (backlog mode only) — R3, R5, R8, R10

**Active only when `PILOT_AUTONOMY=backlog`.** TRIAGE runs **in front of** CLASSIFY: a thin / specless / blocked item never reaches the pipeline. Execute [references/backlog-mode.md](references/backlog-mode.md) Phase 2 — the classification is the **host agent's READ** of the item (its spec body, or the tracker-only issue title+body), never a flowctl field, never a score, never a regex grader, never a second LLM. flowctl supplied facts (Phase 1.5b); the agent supplies judgment here.

**Optional force-gate (R5).** Read the sibling key `pilot.gateClasses` (an array — NOT `pilot.autonomy.gate`). When the selected item matches a configured gate class (the agent's read, like triage — no scorer), route it to `ask` even when otherwise workable:

```bash
# Tolerate BOTH shapes: a JSON array (`["risky"]`) AND a scalar set through the
# CLI — `flowctl config set pilot.gateClasses risky` persists the bare string
# "risky", which `.value[]?` would silently drop. Normalize string→single-class.
GATE_CLASSES="$($FLOWCTL config get pilot.gateClasses --json | jq -r '(.value // empty) | if type=="array" then .[] elif type=="string" then (if startswith("[") then (fromjson | .[]?) else . end) else empty end' 2>/dev/null)"
```

An empty/unset `gateClasses` (the default) gates nothing — full-auto is unconditional. A scalar `flowctl config set pilot.gateClasses risky` is read as the single class `risky`; multiple classes use a JSON array.

Classify `SUBJECT_ID` to exactly one class (first match wins) and route. **Order matters: `dep-unsatisfied` is checked BEFORE `workable`** — a signalled item with an unsatisfied (acyclic) blocker is a dep-wait, NOT a workable advance, so it must route to the dep-wait `BLOCKED` terminal rather than slipping into CLASSIFY/DISPATCH (matches Phase 1f / R10 — a signalled-but-dep-blocked item is selectable and surfaces the wait):

| Class | The agent's read | Route → terminal |
|---|---|---|
| **needs-spec** | a **tracker-only** promoted item — no flow spec exists at all | **ask via tracker comment ALONE** (Phase 3.5) → `ASKED <id> (<n>)`; never a spec stub |
| **dep-unsatisfied** | signal present, but a blocker (flow or tracker) is not yet done | **`BLOCKED <id> by <dep>`** — a state-changing terminal that surfaces the dep wait (a circular/unsatisfiable dep routes to `ASKED` instead, per 1e) |
| **workable** | signal present, **deps satisfied**, AND spec complete enough to act on (clear AC / R-IDs, an actionable next stage), AND not matching a force-gate class | **advance** — set `SELECTED_SPEC="$SUBJECT_ID"` and fall through to Phase 2 CLASSIFY → … → Phase 5 (the existing pipeline, unchanged); terminal `ADVANCED <id> <stage>` |
| **ready-but-thin / ambiguous** | signal present, deps satisfied, but the spec is missing/stub/too-thin to act on safely (or it matched a force-gate class) | **ask** (Phase 3.5) → `ASKED <id> (<n>)` |
| **needs-human** | signal present, deps satisfied, spec exists, but a genuine decision needs a person (conflicting AC, a real design fork) | **ask** (Phase 3.5) → `ASKED <id> (<n>)` |

**The completeness read may only WITHHOLD, never FORCE** (R3): a promoted-but-thin item is kicked back with a question, never built into a slop PR — but the read never overrides an explicit ready signal to *force* work, never sets the ready flag, never promotes.

**A live triage always resolves to a state-changing terminal** (R10): `ADVANCED` / `ASKED` / `BLOCKED` / `NEEDS_HUMAN`. It never ends on a bare `TRIAGED` no-op line — `TRIAGED <id> <class>` is diagnostic / dry-run only. Append the matching decision-log row at the resolving terminal (Phase 6).

**Dry-run is the ONLY case that emits `TRIAGED`, and it short-circuits ALL routing.** Under `--dry-run` (`PILOT_DRY_RUN=1`), backlog triage classifies the subject and STOPS — it never reaches Phase 2 CLASSIFY, Phase 3.5 ASK, the `BLOCKED` terminal, or the Phase 6 pilot-log row. This branch runs immediately after the class is resolved, before any routing:

```bash
if [ "${PILOT_DRY_RUN:-0}" = "1" ]; then
 # $TRIAGE_CLASS = the class resolved above (workable | ready-but-thin | needs-spec | dep-unsatisfied | needs-human).
 echo "PILOT_VERDICT=TRIAGED spec=$SUBJECT_ID stage=triage reason=\"dry-run: classified $TRIAGE_CLASS, nothing dispatched or parked\""
 exit 0
fi
```

When NOT dry-run, route by class: **workable** → set `SELECTED_SPEC="$SUBJECT_ID"` and continue into Phase 2 CLASSIFY (the existing pipeline); every other class → skip Phases 2–5 and resolve in Phase 3.5 (ask) or directly at Phase 6 (`BLOCKED`). A live tick never emits `TRIAGED` (it always lands on a state-changing terminal — R10).

## Phase 2 — CLASSIFY the stage

Resolve the review backend before classification:

```bash
if [[ -n "${PILOT_REVIEW:-}" ]]; then
 REVIEW_BACKEND="$PILOT_REVIEW"
else
 REVIEW_BACKEND="$($FLOWCTL review-backend)" # prints the backend, or ASK when unset
fi
case "$REVIEW_BACKEND" in
 none|ASK|"") REVIEW_CONFIGURED=0 ;;
 *) REVIEW_CONFIGURED=1 ;;
esac
```

Resolve the optional QA-stage gate (fn-72). **Strict** string-enum knob (default `off`): the stage activates **only** on the literal `on` — any other value (`off`, `null`, a coerced bool `true`, or a typo like `maybe`) leaves it off. Read once here and reused by the all-done classification:

```bash
QA_GATE="$($FLOWCTL config get pipeline.qa --json | jq -r '.value')"
if [ "$QA_GATE" = "on" ]; then # ONLY the literal `on` activates — never bool true / typos
 QA_STAGE_ENABLED=1
else
 QA_STAGE_ENABLED=0
fi
```

Classify from `SPEC_JSON` plus `TASKS_JSON`; first match wins:

| Condition | Stage |
|---|---|
| 0 tasks exist | `plan` |
| tasks exist and `plan_review_status != "ship"` and review backend is configured | `plan-review` |
| any task is `todo` or `blocked` (canonical task statuses are `todo`, `in_progress`, `blocked`, `done`) | `work` |
| the only non-`done` tasks are `in_progress` own/unassigned (other-actor claims were already skipped at SELECT) | `NEEDS_HUMAN`, reason `stale in-progress claim — work's ready-driven loop cannot resume it` |
| all tasks done and `completion_review_status != "ship"` and review backend is configured | `work` |
| all tasks done and completion is ship-or-ungated | run the all-done PR probe (below; `--state all`, fails closed): **open PR** → defer-to-land; **closed/merged/probe-failed/missing-branch** → `NEEDS_HUMAN`; **no PR** → `qa` (when `QA_STAGE_ENABLED=1` and no *fresh* `qa_verdict` — R1/R1b) else `make-pr` |

A spec whose only remaining tasks are `blocked` still classifies as `work`; if work cannot advance it, the healthy-no-advance strike path handles it. An in-progress-only spec is different: work's Phase 3a drives off `flowctl ready --spec`, which never returns an `in_progress` task, so dispatching would burn strikes or wrongly enter the completion-review path — the stale-claim `NEEDS_HUMAN` is crash-class (no dispatch, no strike).

Review backend `none` or `ASK` skips both plan-review and completion-review gates; pilot never deadlocks on a gate that cannot run.

### QA-stage freshness probe (R1b — only when `QA_STAGE_ENABLED=1`)

When the QA gate is on, the all-done juncture classifies `qa` **only when no *fresh* `qa_verdict` receipt exists** for the spec. Pilot is single-tick: without this idempotence gate it would re-classify `qa` forever and never reach make-pr. The receipt lives at the committed path `.flow/review-receipts/qa-<spec-id>.json` (the QA skill's default; task .1 added the `head_sha` field). A receipt is **fresh** iff all three hold:

1. `receipt.id == <spec-id>` (the receipt's existing spec-id field is `id`, not `spec`).
2. `receipt.head_sha` matches the spec **branch** head **with the `chore(flow): {qa verdict, pr artifact}` bookkeeping commits peeled off** — the receipt records the CODE head, but pilot commits the receipt (and make-pr the pr.html artifact) ABOVE it, so a raw `rev-parse "$BRANCH_NAME"` would never match and QA would re-run forever. Compute against the branch, not `HEAD` (a resumed/manual tick may sit on another branch); the post-dispatch verify (pre-receipt-commit) still uses `HEAD` directly.
3. `receipt.qa_outcome` is a valid terminal value (`SHIP`, `NEEDS_WORK`, `NA`, or `BLOCKED`).

Resolve `BRANCH_NAME` + `QA_FRESH` here; the `qa` decision itself is made in the all-done PR probe's **no-PR** branch below, so an existing PR always takes priority. Read the receipt with a single `jq` so a missing/malformed file degrades to never-fresh:

```bash
[[ -n "${BRANCH_NAME:-}" ]] || BRANCH_NAME="$(printf '%s\n' "$SPEC_JSON" | jq -r '.branch_name // empty')"
QA_RECEIPT="$REPO_ROOT/.flow/review-receipts/qa-$SELECTED_SPEC.json"
QA_FRESH=0
if [ -f "$QA_RECEIPT" ] && [ -n "$BRANCH_NAME" ]; then
 R_ID="$(jq -r '.id // ""' "$QA_RECEIPT" 2>/dev/null)"
 R_SHA="$(jq -r '.head_sha // ""' "$QA_RECEIPT" 2>/dev/null)"
 R_OUT="$(jq -r '.qa_outcome // ""' "$QA_RECEIPT" 2>/dev/null)"
 case "$R_OUT" in SHIP|NEEDS_WORK|NA|BLOCKED) : ;; *) R_SHA="" ;; esac # invalid outcome → never fresh
 # The receipt's head_sha is the CODE head; pilot's own `chore(flow): qa verdict` commit
 # (and a later `pr artifact` commit) sit ABOVE it on the branch, so the branch tip is not
 # the code head. Walk from the tip peeling those bookkeeping commits and accept a match
 # anywhere in the chain — else a successful QA pass reads as never-fresh and re-runs forever.
 if [ "$R_ID" = "$SELECTED_SPEC" ] && [ -n "$R_SHA" ]; then
 _s="$(git -C "$REPO_ROOT" rev-parse --verify --quiet "$BRANCH_NAME" 2>/dev/null || echo "")"
 while [ -n "$_s" ]; do
 [ "$_s" = "$R_SHA" ] && { QA_FRESH=1; break; }
 git -C "$REPO_ROOT" log -1 --format='%s' "$_s" 2>/dev/null \
 | grep -qE '^chore\(flow\): (qa verdict|pr artifact) ' || break
 _s="$(git -C "$REPO_ROOT" rev-parse "$_s^" 2>/dev/null || echo "")"
 done
 fi
fi
```

`QA_FRESH` feeds the **no-PR branch** of the all-done PR probe below — the `qa` decision is made *there*, not before it. Classify `qa` only when that probe finds **no PR** AND `QA_STAGE_ENABLED=1` AND `QA_FRESH=0`. Any existing PR takes priority over (re-)running QA (open → defer-to-land; closed/merged/probe-failed → `NEEDS_HUMAN`), and the probe **fails closed** on a `gh` error — so a transient API failure never misroutes to `qa`. A fresh receipt (`QA_FRESH=1`) or the gate off ⇒ `make-pr`. (Echo `qa_gate=<on|off> qa_fresh=<0|1>` in the classification report so a transcript-only driver sees why the juncture chose `qa` vs `make-pr`.)

The all-done PR probe is the only gh touch in classification. Resolve the spec's `branch_name` first (Phase 3 reuses the same `BRANCH_NAME`):

```bash
BRANCH_NAME="$(printf '%s\n' "$SPEC_JSON" | jq -r '.branch_name // empty')"
PR_PROBE_FAILED=0
PR_JSON=$(gh pr list --head "$BRANCH_NAME" --state all --json url,state,number --limit 10 2>/dev/null) || PR_PROBE_FAILED=1
OPEN_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "OPEN") | .url' | head -1)
CLOSED_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "CLOSED") | .url' | head -1)
MERGED_PR=$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '.[] | select(.state == "MERGED") | .url' | head -1)
```

Classification outcomes for the all-done branch (the all-done invariant: an all-done / completion-`ship` spec lacking a **merged** PR is *unfinished from the board's perspective* — pilot keeps driving it (`make-pr`), defers it to land (open PR), or surfaces it (`NEEDS_HUMAN`); it never collapses to terminal `NO_WORK`):

- gh missing, unauthenticated, or API failure: `PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=make-pr reason="gh probe failed at all-done branch"`.
- OPEN PR exists (and no MERGED PR): this spec is **deferred to land** — land owns the open PR, not pilot — so record it as a *deferred candidate* and skip to the next SELECT candidate. This is an explicit defer, never a silent finish: if no later candidate is selectable, the tick terminates with the distinct, greppable `PILOT_VERDICT=DEFERRED_TO_LAND` line (Phase 6), never `NO_WORK`. Track the deferred spec id + open-PR url so the terminal line can name it.
- No PR exists: classify `qa` when `QA_STAGE_ENABLED=1` **and** `QA_FRESH=0` (the optional QA stage runs before make-pr); otherwise `make-pr`. This is the FLOW-15 case (all-done, no PR — make-pr never ran or its PR was lost); it MUST classify `qa`/`make-pr` and never fall through to `NO_WORK`.
- CLOSED PR exists and no OPEN PR exists: `NEEDS_HUMAN`, because the PR was closed without merge and pilot never silently reopens human-rejected work.
- MERGED PR exists while the spec is still open: `NEEDS_HUMAN`, because the state is inconsistent and pilot must not create a second PR.

Dry-run stops after classification. It prints selected spec, stage, review backend, task counts, consulted status fields, PR probe result if any, skipped candidates, and any would-clear ledger entries. It writes no ledger (the ledger file is never created or modified on a dry-run tick), checks out no branch, and dispatches nothing:

```text
PILOT_VERDICT=NO_WORK spec=<id> stage=<stage> reason="dry-run: classification only, nothing dispatched"
```

## Phase 3 — Branch resolution matrix

Pilot owns branch resolution. Reuse `BRANCH_NAME` from Phase 2 (resolve it here when classification never reached the all-done branch):

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
| branch absent and stage is first `work` tick | dispatch work with `--branch=new`; under autonomy work names it exactly the spec's `branch_name` (fn-59.2 contract), so later ticks find it |
| stage is `qa` and branch exists | `git checkout <branch_name>`; QA drives the running app against this branch's build (never the default branch — the app under test is the spec's build). After checkout `HEAD` equals the branch head, so the Phase 5 post-dispatch freshness verify uses `HEAD`. |
| stage is `qa` and branch absent | `NEEDS_HUMAN`, reason `all tasks done but spec branch missing — inconsistent state` (all-done with no branch is the same inconsistency as the make-pr row; QA never silently skips) |
| stage is `make-pr` and branch exists | `git checkout <branch_name>`; make-pr auto-detects the spec from the branch |
| stage is `make-pr` and branch absent | `NEEDS_HUMAN`, reason `all tasks done but spec branch missing — inconsistent state` |
| stage is `plan` or `plan-review` | `git checkout` the default branch (local `main`, else `master`) |

The plan/plan-review checkout matters in multi-spec loops: a prior tick's make-pr leaves the worktree on that spec's PR branch, and planning state written there would mutate the already-open PR.

If branch checkout fails (any matrix row, including the default-branch checkout), stop with `NEEDS_HUMAN`; do not dispatch and do not strike.

## Phase 4 — DISPATCH exactly one sub-skill

Record the pre-dispatch evidence snapshot before invoking the stage skill:

- `plan`: task count from `$FLOWCTL tasks --spec <id> --json`.
- `plan-review`: `plan_review_status` from `$FLOWCTL show <id> --json`.
- `work`: per-task id/status list, spec status, and `completion_review_status`.
- `qa`: absence of a fresh `qa_verdict` receipt (`QA_FRESH=0`), already proven by the classify-time freshness probe; the post-dispatch verify re-reads the receipt against the **code head** (HEAD peeled past the qa-verdict bookkeeping commit).
- `make-pr`: no OPEN PR for the branch, already proven by the all-done probe.

**Backlog mode — guard the dispatch (invariant #1).** When `PILOT_AUTONOMY=backlog`, set `DISPATCH_TARGET` to the stage's slash command and call the allowlist assert immediately before invoking it — a forbidden merge/land/resolve target hard-exits `NEEDS_HUMAN` rather than dispatching:

```bash
if [ "${PILOT_AUTONOMY:-ready}" = "backlog" ]; then
 DISPATCH_TARGET="/flow-next:$STAGE" # e.g. /flow-next:work
 assert_allowed_dispatch "$DISPATCH_TARGET"
fi
```

Dispatch exactly one existing stage skill (slash-command invocation), with `mode:autonomous` and `FLOW_AUTONOMOUS=1` semantics for any process-level work it starts:

- `plan`: `/flow-next:plan <spec-id> mode:autonomous --research=<grep|rp> --depth=<level> --review=<backend>`
- `plan-review`: `/flow-next:plan-review <spec-id> --review=<backend>`
- `work`: `/flow-next:work <spec-id> mode:autonomous --branch=<current|new> --review=<backend>`
- `qa`: `/flow-next:qa <spec-id> mode:autonomous` — the QA skill derives scenarios from the spec, reads work's evidence, drives the **local running app**, and writes the `qa_verdict` receipt. `mode:autonomous` suppresses all prompts (the QA skill's Autonomous-mode gate) so the loop can't hang on a question prompt. Pilot dispatches the existing skill and never re-implements its logic; routing on the resulting `qa_outcome` is Phase 5.
- `make-pr`: `/flow-next:make-pr <spec-id> mode:autonomous`

Setter convention call-out: plan-review sets `plan_review_status` itself in its workflow Phase 4, and pilot only re-reads the field. Completion review is reached through work's Phase 3g; work invokes spec-completion-review, then the caller sets `completion_review_status=ship`. Pilot must not dispatch completion review directly.

If a sub-skill crashes, asks for judgment under autonomy, or reports ambiguity that needs a person, stop with `NEEDS_HUMAN`. Do not cleanup, reset claims, or record a strike.

## Phase 5 — VERIFY + evidence echo

Re-read state after dispatch. Judge advancement only on observed state, never sub-skill narration. Echo the before/after evidence block so a transcript-only driver can validate it.

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

For `work`, advancement means at least one task/spec status transition occurred, or `completion_review_status` newly became `ship` when that gate was the work to do:

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

For `qa`, advancement is judged from the **post-dispatch `qa_verdict` receipt** — observed state, never the QA skill's narration. The QA stage **advances on every terminal outcome**: the gate routes on `qa_outcome` (the four-outcome field), NOT the Ralph-guard `verdict` projection (the QA skill projects `BLOCKED→verdict=NEEDS_WORK`, so reading `verdict` would wrongly conflate "couldn't verify" with "found problems"). QA is advisory — it never hard-blocks the build loop; the human reviewer + the land gate act on its findings.

Read the receipt fresh after dispatch. The QA skill commits its own handoff in autonomous mode (qa §6.3b), so `HEAD` is now the `chore(flow): qa verdict` commit — peel it to the **code head** and match the receipt's `head_sha` against that (the pr-artifact commit can't exist yet — that's the next tick's make-pr):

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
 # head, terminal outcome. A missing/stale receipt (qa errored before writing) ⇒
 # advanced=false — never advance on narration.
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

Routing on the **fresh** `qa_outcome` (`QA_ADVANCED=true`):

- `SHIP` / `NA` / `BLOCKED` → advance cleanly to the next tick's make-pr (BLOCKED = no local app reachable / NA = no driveable UI; both advance — QA is the optional augmenting pass, never a wedge).
- `NEEDS_WORK` → **still advance** (the build loop never stalls on QA). The findings ride the draft PR: make-pr surfaces them from the receipt (its §2.x QA-summary section), and the QA skill already filed them to the bug-memory track + (when the bridge is active) the tracker comment. A `NEEDS_WORK` qa stage is an `ADVANCED` verdict, not `BLOCKED`/`NEEDS_HUMAN`.

**The QA skill commits its own handoff** (the `qa_verdict` receipt + the exact bug-memory it filed) in autonomous mode (qa §6.3b) — so the receipt is already on the branch and rides the eventual make-pr push. **Pilot adds no commit of its own here**: the agent that wrote the files commits them precisely, so pilot never sweeps the tree or guesses paths.

A missing/stale receipt (`QA_ADVANCED=false`) is the healthy-no-advance path (Phase 6 strike), NOT a crash — the QA skill ran but produced no fresh verdict (e.g. it errored before writing). **Don't-thrash + non-fatal:** pilot is single-tick and the freshness gate prevents re-classifying `qa` once a fresh receipt exists, so the same spec is bounded to one qa pass per branch-head; the interactive work↔qa re-pass (out of scope here — autonomous surfaces + proceeds) is bounded by the existing strike/auto-block reflexes (2 strikes → unready). `BLOCKED` from a missing app is a fresh terminal outcome (it advances), never a failed loop.

For `make-pr`, advancement means a gh-confirmed OPEN PR URL for the branch. There is no flowctl transition for make-pr, and a successful PR tick must never record a strike:

```bash
OPEN_PR_URL=$(gh pr list --head "$BRANCH_NAME" --state all --json url,state,number --limit 10 2>/dev/null \
 | jq -r '.[] | select(.state == "OPEN") | .url' \
 | head -1)
```

Echo the URL when present:

```text
Evidence:
stage=make-pr
open_pr.before=-
open_pr.after=<url>
advanced=<url present>
```

If the post-dispatch tree is dirty outside `.flow/`, stop with `NEEDS_HUMAN` and leave state for diagnosis. This is a crash-class outcome, not a strike.

If the sub-skill emitted a `Tracker sync:` summary line, pass that line through in the evidence echo. Pilot never re-checks the tracker itself.

## Phase 3.5 — ASK (backlog mode only, non-workable subjects) — R4, R7, R15

**Active only when `PILOT_AUTONOMY=backlog` AND Phase 1.6 routed the subject to `ask`** (ready-but-thin / needs-spec / needs-human / force-gated). Execute [references/backlog-mode.md](references/backlog-mode.md) Phase 3 — the async question valve. **Never asks interactively** (`plain-text numbered prompt` is forbidden on the tick path — the human answers later via the spec or the tracker).

**Enforce invariant #2 inline before any spec-side write.** A spec-backed subject writes `## Open Questions`; a tracker-only subject (empty/absent `SPEC_PATH`) must hard-exit rather than author a spec stub. Call the assert with the resolved paths, then guard the dispatch (invariant #1):

```bash
# Spec-backed: SPEC_PATH points at an EXISTING spec file → the assert passes and the op writes the
# `## Open Questions` anchor. Tracker-only: SPEC_PATH is empty → the assert hard-exits, so the op is
# invoked WITHOUT touching any spec (the question lives in the tracker comment alone). Run the assert
# ONLY when a spec-side write is intended (HAS_SPEC=1); a tracker-only subject skips it and parks in
# the tracker.
[ "${HAS_SPEC:-0}" = "1" ] && assert_spec_write_allowed "$SUBJECT_ID" "$SPEC_PATH"
DISPATCH_TARGET="/flow-next:tracker-sync question"; assert_allowed_dispatch "$DISPATCH_TARGET"
```

The question is then posted via tracker-sync's transport-blind `question` op (it owns the stable-anchor authoring, comments-sync dedup, and the answer round-trip — backlog mode invokes it, never re-implements it):

```text
/flow-next:tracker-sync question <SUBJECT_ID> mode:autonomous # <SUBJECT_ID> = spec id OR tracker id
```

Where the question parks depends on whether a spec exists — enforced by safety invariant #2 (never author a spec):

- **Spec-backed** (`HAS_SPEC=1`, `SPEC_PATH` exists) — the durable parked state lives in the spec's `## Open Questions` behind the `<!-- flow-next:question id=… status=open -->` anchor (the floor), AND it is mirrored as a tracker comment when the bridge is active. The op writes both. A context-package is included (what's blocked, why, what each answer would do, the spec id + tick).
- **Tracker-only** (`HAS_SPEC=0`, no spec) — there is no spec to anchor in, so the question lives in the **tracker comment ALONE**. The surfaced gap is always *"this promoted ticket has no flow spec — run `/flow-next:capture` or `/flow-next:interview`"*. **Never write a spec stub** (invariant #2 short-circuits a spec write for a specless subject). Its parked/answered state lives in the tracker.

**Idempotent (R7/R15).** Re-triaging the same blocked subject computes the same anchor `id` (the hash covers stable fields only — `subjectId` + blocked-stage + `reasonCode` + `questionSlug`; the free prose is outside it), so comments-sync's marker dedup finds the existing comment and skips the re-post. Selection (Phase 1.5d) already skips a `status=open` parked subject, so a parked item is not re-picked.

**Spec-first floor (R17).** When no transport is reachable, the question is written to the spec's `## Open Questions` only (when a spec exists) plus a one-line "enable tracker-sync to mirror" note — never a block. A tracker-only item with no transport has nowhere to park; that degrades to a `NEEDS_HUMAN` surface (the gap cannot be recorded), never a silent drop.

The terminal is `ASKED <id> (<n>)` — a **durable park** (the `status=open` anchor makes Phase 1.5d skip it next tick). Count `<n>` = open questions surfaced. Append the `asked` decision-log row (Phase 6) and emit:

```text
PILOT_VERDICT=ASKED spec=<id> stage=ask reason="parked behind <n> open question(s): <one line>"
```

(`spec=<id>` is the spec id for a spec-backed subject, else the tracker id for a tracker-only subject.)

## Phase 6 — REPORT + strikes ledger

On `ADVANCED`, clear the selected spec's ledger entry if present and write the ledger atomically with `jq` plus `mv`:

```bash
mkdir -p "$LEDGER_DIR"
[ -s "$LEDGER" ] || echo '{}' > "$LEDGER"
tmp="$LEDGER.tmp.$$"
jq --arg spec "$SELECTED_SPEC" 'del(.[$spec])' "$LEDGER" > "$tmp" && mv "$tmp" "$LEDGER"
```

Then print the terminal line:

```text
PILOT_VERDICT=ADVANCED spec=<id> stage=<stage> reason="<what advanced>"
```

For a `qa` stage the reason names the fresh `qa_outcome` so a transcript-only driver sees the result without re-reading the receipt, e.g. `reason="qa pass: qa_outcome=NEEDS_WORK — findings surfaced on draft PR"` or `reason="qa pass: qa_outcome=BLOCKED — no local app reachable, advancing"`. Every fresh terminal `qa_outcome` (SHIP/NEEDS_WORK/NA/BLOCKED) is an `ADVANCED` — QA is advisory and never `BLOCKED`/`NEEDS_HUMAN` on its own outcome; only a *missing/stale* receipt routes to the healthy-no-advance strike below.

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

If `STRIKE_COUNT` is `1`, leave the spec ready and print:

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="no advancement (strike 1/2): <why>"
```

If `STRIKE_COUNT` is `2`, unready the spec, keep the ledger reason, and print:

```bash
$FLOWCTL spec unready "$SELECTED_SPEC"
```

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="no advancement (strike 2/2, spec unreadied): <why>"
```

### Backlog-mode dep-wait `BLOCKED` terminal (R10 — distinct from the strike path)

**Active only when `PILOT_AUTONOMY=backlog` AND Phase 1.6 routed the subject to `dep-unsatisfied`.** This is a SEPARATE `BLOCKED` terminal from the strike-based one above: it is a clean **dep-wait surface** (the selected, signalled item has an acyclic-but-unsatisfied blocker — Phase 1.6 / Phase 1f), **not** a no-advancement failure. It records **no strike** (the spec is healthy — it is simply waiting on a blocker the topo-sort offers first on a later tick), does **not** unready the spec, and writes the `blocked` decision-log row (the dep-wait, not a strike). `<dep>` is the unsatisfied blocker id (flow `blockedBy` edge or tracker relation); name the first when several:

```bash
# No ledger write — a dep wait is healthy, not a strike. STAGE is the stage the
# item would advance to once unblocked (or '-'); $SUBJECT_ID is spec-backed or a
# tracker key. The `blocked` action distinguishes the dep wait from the strike path.
$FLOWCTL pilot-log append --id "$SUBJECT_ID" --action blocked --stage "${STAGE:--}" ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"}
```

```text
PILOT_VERDICT=BLOCKED spec=<id> stage=<stage> reason="dep wait — blocked by <dep> (not yet done); topo-sort offers the blocker first next tick"
```

(A circular/unsatisfiable dep does NOT reach here — Phase 1e routes it to `ASKED` instead. This terminal is for the plain acyclic dep wait only.)

Crash-class outcomes are `NEEDS_HUMAN`: sub-skill crash, dirty non-`.flow/` tree after dispatch, gh probe failure in the all-done branch, branch inconsistency, closed-without-merge PR, merged-PR-but-open-spec, stale in-progress-only claim, or autonomy ambiguity. Leave state untouched and record no strike:

```text
PILOT_VERDICT=NEEDS_HUMAN spec=<id> stage=<stage> reason="<one line>"
```

An all-done spec with an **open** PR is *not* crash-class — it is the benign `DEFERRED_TO_LAND` terminal below (land owns the merge). Only the closed-unmerged, missing-branch, and merged-but-open-spec all-done states are `NEEDS_HUMAN`. An all-done spec with **no** PR is never terminal at all — it classifies `make-pr` and dispatches.

Terminal verdict when no spec was dispatched, split by why — the two cases are distinct and must never be conflated:

- **No selectable candidate at all** (none open+ready, or all skipped for unsatisfied deps / other-actor claims) yields `NO_WORK`:

 ```text
 PILOT_VERDICT=NO_WORK spec=- stage=- reason="no ready spec with satisfied deps"
 ```

- **Every remaining candidate was deferred to land** (each all-done with an existing OPEN PR — the only reason they weren't dispatched) yields the distinct, greppable `DEFERRED_TO_LAND` verdict, naming the deferred spec so a transcript-only driver can hand it to `/flow-next:land`. This case MUST NOT collapse to `NO_WORK`: a `DONE`-but-open-PR spec is real outstanding work that land owns, not absence of work.

 ```text
 PILOT_VERDICT=DEFERRED_TO_LAND spec=<id> stage=land reason="all tasks done, open PR <url> — land owns the merge"
 ```

 When more than one candidate was deferred, name the first deferred spec (stable id order) in the line; the reason still reads `defer to land`.

### Backlog-mode decision log (R9) — one row per tick, at the resolving terminal

**Active only when `PILOT_AUTONOMY=backlog`.** Every backlog tick that selected a subject appends exactly **one** decision-log row, keyed to the verdict grammar action, at its resolving terminal. The row co-occurs with the state-changing terminal — a live `TRIAGED` is never a bare no-op, so the logged action is always a terminal action (R10). Stored under `.flow/pilot-runs/` (a sync-runs-style dir, NOT a ralph-guard `receipts/` path), auto-gitignored:

```bash
# ACTION ∈ {advanced, asked, blocked, needs-human} (mapped from the terminal verdict)
# ADVANCED → advanced · ASKED → asked · BLOCKED → blocked · NEEDS_HUMAN → needs-human
# STAGE is the pipeline stage advanced/blocked-at, or 'ask' for ASKED, or '-' when none.
# COST_TOKENS is host-reported (this tick's token cost); omit the flag when unavailable.
$FLOWCTL pilot-log append --id "$SUBJECT_ID" --action "$ACTION" --stage "${STAGE:--}" ${COST_TOKENS:+--cost-tokens "$COST_TOKENS"}
```

- **`--id`** takes the spec id (spec-backed) OR the bare tracker key (tracker-only) — flowctl safe-filename-normalizes it.
- **`--action`** is the frozen enum `triaged|advanced|asked|blocked|needs-human`. A **live** tick logs only the terminal action (`advanced`/`asked`/`blocked`/`needs-human`); `triaged` is for a diagnostic/dry-run inspection only, matching the `TRIAGED` diagnostic-only verdict.
- **`--cost-tokens`** is host-reported by the skill (flowctl only stores the row; it never measures cost). Omit the flag when the host cannot report it.

A `NO_WORK` / `DEFERRED_TO_LAND` tick selected no subject, so it writes **no** row (there is nothing to log against). A `--dry-run` tick writes no row (classification/inspection only). The single-tick contract holds: exactly one row per acting backlog tick.

**The dep-wait `BLOCKED` terminal above already emits its own `--action blocked` row inline** — that IS its single decision-log row, so do NOT append a second one here for that path. This generic block covers the other resolving terminals (`advanced` / `asked` / `needs-human`) and the strike-based `BLOCKED`. Whichever terminal resolves the tick writes exactly **one** `blocked` row, never two.

The `PILOT_VERDICT` line is always the last line of the tick output. Print nothing after it.
