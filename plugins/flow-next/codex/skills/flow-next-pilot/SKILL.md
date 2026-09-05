---
name: flow-next-pilot
description: Single-tick autonomous build-loop conductor. One spec or the backlog, one stage per tick (pipeline.chainStages chains qa into make-pr), emits PILOT_VERDICT. Use when asked to pilot a spec or backlog.
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit, Skill
---

# /flow-next:pilot — single-tick autonomous build-loop conductor

A tick is one invocation of `/flow-next:pilot`: select one ready spec, classify its current stage (`plan`, `plan-review`, `work`, the opt-in `qa`, `make-pr`), dispatch exactly one existing stage skill (with `pipeline.chainStages` on, `make-pr` after a fresh `qa` verdict is the only admissible second dispatch in the same tick), verify state advanced, and end with one terminal `PILOT_VERDICT` line. It is intentionally not a runner; `/loop` in Claude Code or `/goal` in Claude Code / Codex owns repeated invocation.

Pilot and Ralph are alternative autonomous drivers. Ralph is an external shell loop with receipt plumbing; pilot is an in-session conductor for host loop primitives. Never nest them, and never reuse Ralph harness state inside pilot.

Human judgment lives before pilot: the spec content, `depends_on_epics`, and the fn-58 `ready` gate are the consent boundary. Pilot executes the mechanical pipeline one stage at a time, with ambiguity reported as `NEEDS_HUMAN`.

### Chart is outside the build loop (fn-135)

Chart is optional pre-capture discovery - **never** a pilot pipeline stage. Pilot never advances a chart tick. Optional unattended chart driving (host `/loop` on `/flow-next:chart`) stops **terminally** at attended decisions (`CHART_VERDICT=NEEDS_HUMAN`) - pilot does not absorb or continue that work. Capture, interview, and chart stay human-gated upstream of the ready consent boundary.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`. Subagents that run in fresh context fall back to the repo-local copy:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

Cold session / tick start: `$FLOWCTL brief` first for session-scope orientation (one budgeted call).

**Re-read this skill file at every tick start.** A long `/loop` run executing from a stale in-context copy drifts from the file the repo actually ships — the file on disk is the contract, the remembered copy is not.

**Probe an idle dispatched agent read-only** — its side effects (commits, receipts, status fields), never a resume message: a resume restarts the agent, so "checking on" an agent that was merely slow turns one run into two.

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
PILOT_BACKLOG_OVERRIDE=""   # "" = use config; "1" = force backlog (--backlog/--auto)

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
    --backlog|--auto) PILOT_BACKLOG_OVERRIDE=1 ;;
    --review=*)   PILOT_REVIEW="${ARG#--review=}" ;;
    --research=*) PILOT_RESEARCH="${ARG#--research=}" ;;
    --depth=*)    PILOT_DEPTH="${ARG#--depth=}" ;;
    -*) echo "Unknown flag: $ARG (ignored by /flow-next:pilot)" >&2 ;;
    *)  echo "Unknown argument: $ARG (ignored by /flow-next:pilot)" >&2 ;;
  esac
done
[[ -n "$PREV" ]] && echo "Flag $PREV given without a value (ignored by /flow-next:pilot)" >&2
export PILOT_SPEC PILOT_DRY_RUN PILOT_REVIEW PILOT_RESEARCH PILOT_DEPTH PILOT_BACKLOG_OVERRIDE
```

No branch flag exists in v1. Branch resolution is pilot-owned from the selected spec's `branch_name`.

Pilot has no no-plan flag (fn-214): the no-plan decision is spec state — the `no_plan` field, set at capture time or via `flowctl spec set-no-plan`, read from `SPEC_JSON` at classification. A stray `--no-plan` argument lands in the unknown-flag branch above (one-line notice, tick proceeds; the affected zero-task specs classify `plan`, the safe default). Pilot never decides no-plan on its own — the field is an explicit human instruction on the item, never inferred, and pilot only forwards it to the work dispatch.

### Autonomy mode resolution (R1) — gate the wide backlog behavior

Resolve `PILOT_AUTONOMY` once, here, so every downstream block keys off a single value. This block also captures the tick's ROOT CONFIG SNAPSHOT (fn-110) — the ONLY `config get` invocation across all pilot files (SKILL.md, workflow.md, references/backlog-mode.md): workflow.md's `pipeline.qa` probe and the `pilot.gateClasses` reads derive from the snapshot file via jq, never a second config call. The gate is a **strict scalar string-enum** — backlog mode activates **only** on the literal `backlog` (config `pilot.autonomy`), or when the per-run `--backlog` / `--auto` flag forced the override. Any other config value (`ready`, `null`, a coerced bool `true`, a typo) leaves pilot in `ready` mode — **byte-for-byte unchanged behavior** (the `references/backlog-mode.md` file is never even read):

```bash
# Root config snapshot: {"key":null,"value":{<merged config>}}. Persisted to a file
# because bash vars do not survive across prompt turns; later fences RECOMPUTE this
# same deterministic repo-hash-keyed path and jq it. The path lives under
# ${TMPDIR} — NEVER under repo-controlled .flow/tmp (autonomous symlink safety:
# a committed symlink must not redirect this write out of tree) — so a dry-run
# tick mutates nothing inside the repo; dry-run terminals also `rm -f` this
# snapshot (workflow.md), leaving no persistent scratch state. On capture
# FAILURE remove the file —
# downstream jq reads then error, which keeps the pipeline.qa probe's fail-open
# contract (probe error ⇒ ACTIVE) intact.
PILOT_CFG_SNAPSHOT="${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json"
rm -f "$PILOT_CFG_SNAPSHOT" 2>/dev/null   # drop any stale/planted file (incl. a symlinked leaf) before the fresh write
$FLOWCTL config get --json > "$PILOT_CFG_SNAPSHOT" 2>/dev/null \
  || rm -f "$PILOT_CFG_SNAPSHOT"
PILOT_AUTONOMY="$(jq -r '.value.pilot.autonomy' "$PILOT_CFG_SNAPSHOT" 2>/dev/null)"
if [ "$PILOT_BACKLOG_OVERRIDE" = "1" ]; then
  PILOT_AUTONOMY="backlog"                       # --backlog / --auto forces backlog this run
elif [ "$PILOT_AUTONOMY" != "backlog" ]; then
  PILOT_AUTONOMY="ready"                         # ONLY the literal `backlog` enables — never bool true / typos / null
fi
export PILOT_AUTONOMY
```

When `PILOT_AUTONOMY=ready` (the default), pilot behaves exactly as documented in `workflow.md` Phases 1–6 — no backlog-mode code path runs and `references/backlog-mode.md` is not loaded. When `PILOT_AUTONOMY=backlog`, **read [references/backlog-mode.md](references/backlog-mode.md) top to bottom, execute its backlog-only setup, then continue with `workflow.md` Phase 1**. The reference owns the backlog-only verdict extension plus SELECT/TRIAGE/ASK context; `workflow.md` keeps the enforcing guards and action sites.

## The verdict contract (read this before the workflow)

The `/goal` validator is transcript-blind: it reads conversation output only and never runs tools. Every tick therefore echoes its verification evidence into the output: flowctl status fields, task counts, task status transitions, and the gh-confirmed PR URL for make-pr.

Every tick ends with exactly one terminal line, the last line of the response,
with nothing after it. The common ready-mode grammar is:

```text
PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"
```

Use `spec=-` and `stage=-` when no spec was selected. Stage values are exactly
`plan`, `plan-review`, `work`, `qa` (opt-in — only when `pipeline.qa==on`),
`make-pr`, `land`, or `-`. A chained tick (`pipeline.chainStages==on`) names every
dispatched stage in order joined by `+` — exactly `qa+make-pr` — and carries the
last dispatched stage's verdict.

**Dry-run snapshot cleanup.** Under `--dry-run` (`PILOT_DRY_RUN=1`), at EVERY terminal `PILOT_VERDICT` emission — the classification stop, the diagnostic `TRIAGED` exit, every `NO_WORK` / `DEFERRED_TO_LAND` / hard-guard exit — remove the root config snapshot BEFORE printing the verdict, so a dry-run leaves no persistent scratch state:

```bash
rm -f "${TMPDIR:-/tmp}/flow-pilot-config-$(git rev-parse --show-toplevel 2>/dev/null | cksum | cut -d' ' -f1).json"
```

Recompute the path exactly as above (vars die across prompt turns). Live (non-dry-run) ticks keep the snapshot for the tick's remaining fences; it is overwritten fresh by the next tick's capture. Never blocks, fail-open (`rm -f` on a missing file is a no-op).

`DEFERRED_TO_LAND` is a distinct *non-terminal-work* verdict (stage `land`): every remaining all-done candidate has an open PR that land — not pilot — owns. It is deliberately separated from `NO_WORK` so a driver can route it to `/flow-next:land` instead of stopping; an all-done spec with an open PR is real outstanding work, never absence of work.

Driver condition examples:

```text
/goal keep running /flow-next:pilot until it prints PILOT_VERDICT=NO_WORK, or stop after 20 turns
/goal keep running /flow-next:pilot --review=codex until PILOT_VERDICT=NO_WORK or PILOT_VERDICT=NEEDS_HUMAN
```

## Forbidden

- Asking the user anything in the tick path. Pilot is autonomous; ambiguity maps to `NEEDS_HUMAN`. In backlog mode, ambiguity that needs a person is surfaced **async** via the `ask` stage (`ASKED`) — never an interactive `plain-text numbered prompt`.
- Dispatching any skill outside the stage set `{plan, plan-review, work, make-pr}` - plus `qa` **only when `pipeline.qa==on`** (fn-72: an opt-in, gate-reversed stage at the all-done juncture before make-pr; with the gate off, `qa` is forbidden and the stage set is byte-for-byte unchanged). **Backlog mode (`PILOT_AUTONOMY=backlog`) additionally invokes `/flow-next:tracker-sync` for the `reconcile` / `list-open` / `list-comments` / `list-relations` / `question` ops** - these are read/surface-only tracker calls (`list-comments` reads parked question rounds; `list-relations` reads dependency relations for dep-ordering), not a pipeline stage, and run only on the backlog path. Capture, interview, chart, resolve-pr, merge, and release are **never** pilot stages - they stay forbidden for their distinct reasons (capture/interview/chart are human authoring and discovery upstream of the consent boundary; resolve-pr/merge/release are land's territory downstream of the PR). **Opening `qa` under its gate, or `tracker-sync` under backlog mode, sets no precedent for any of those** — a tick that dispatched one of them by analogy has broken this.
- Dispatching a second stage in one tick — except, under `pipeline.chainStages==on`, `make-pr` after this tick's `qa` verified a fresh terminal verdict (the closed one-row chain table in `workflow.md` Phase 5, Chained stage); any other second dispatch breaks the single-tick contract.
- Re-implementing sub-skill logic. Pilot owns selection, dispatch, verification, verdicts, and the strikes ledger only. The backlog-mode SELECT/TRIAGE/ASK workflow lives in `references/backlog-mode.md` (loaded only when `PILOT_AUTONOMY=backlog`); the question-anchor authoring + answer round-trip live in tracker-sync — backlog mode invokes them, never re-implements them.
- **Never merging / never invoking land** (R6) — in either mode, the terminus is `make-pr` (draft). Merge stays human-gated. Backlog mode never calls `/flow-next:land`, `gh pr merge`, or any merge path.
- **Never authoring a spec** (backlog mode) — `capture`/`interview` are human-gated upstream. A missing/too-thin spec is surfaced as a "needs capture/interview" gap and parked (`ASKED`), never auto-written. The only writing the `ask` stage may do is fill an obvious blank in an *existing* spec — never create a spec stub from a bare ticket.
- Touching gh anywhere except the all-done classification branch's PR probe and the make-pr verification probe.
- Printing anything after the `PILOT_VERDICT` line.
- Running under Ralph (`FLOW_RALPH` / `REVIEW_RECEIPT_PATH`).

## Workflow

Execute [workflow.md](workflow.md) in order:

1. **guards** — refuse Ralph nesting, refuse dirty non-`.flow/` start state, resolve the `.git` strikes ledger (read-only at this point). *Done when: both guards have passed and `LEDGER_JSON` is loaded without a write.*
2. **select** — two-pass ready-spec selection with dependency, claim, and re-bless checks. *Done when: exactly one spec is selected, or the pool is empty and the terminal split has been chosen.*
3. **classify** — derive one stage from flowctl state; probe gh only in the all-done branch. *Done when: exactly one stage from the allowed set is named, with the consulted status fields echoed.*
4. **branch** — resolve the spec branch matrix before work or make-pr. *Done when: the worktree sits on the branch the matrix row names, or the tick has stopped `NEEDS_HUMAN` on a failed checkout.*
5. **dispatch** — invoke exactly one stage skill with `mode:autonomous` plus review/research/depth passthroughs (plus the gated `qa`→`make-pr` chain when `pipeline.chainStages` is on). *Done when: the classified stage skill has been invoked and returned — and, on a chained tick, so has `make-pr`; no other second dispatch happened.*
6. **verify** — re-read flowctl state, or gh for make-pr, and echo before/after evidence. *Done when: every dispatched stage has its own before/after evidence block plus stage-outcome line in the transcript and each `advanced` is decided from observed state.*
7. **report** — clear or record strikes, optionally unready on the second healthy no-advance tick, and print the terminal verdict. *Done when: the ledger reflects this tick and the terminal `PILOT_VERDICT` line is the last line of the response.*

**Backlog mode (`PILOT_AUTONOMY=backlog`).** When the autonomy gate resolved to `backlog`, the SELECT and TRIAGE/ASK behavior follows [references/backlog-mode.md](references/backlog-mode.md) — the agentic floor scheduler (loaded **only** in this mode). It widens SELECT (pull-before-scan, union tracker-only items, dep-order, skip parked) and adds the `triage`/`ask` stages **in front of** CLASSIFY; a **workable** item flows into the existing `classify → branch → dispatch → verify` path unchanged. `workflow.md` Phase 0.5 resolves the mode and routes; `workflow.md` Phase 1.5/Phase 3.5 carry the backlog SELECT + TRIAGE/ASK hooks and the safety invariants. The single-tick contract is unchanged: one item, one stage (or the gated `qa`→`make-pr` chain under `pipeline.chainStages`) or one durable park, one terminal verdict.

## Unattended runs — rp caveat

The `rp` review backend runs headlessly through the CE-first CLI ladder — it needs RepoPrompt CE running on the same Mac (cold start: `open -ga "RepoPrompt CE"`; a stopped app fails fast). Classic is only the final compatibility fallback. On remote/CI machines, use `--review=codex`, `--review=copilot`, `--review=cursor`, `--review=claude` (Claude-family verdict from any host; same-family on Claude Code, recorded in the receipt), `--review=host` (host-native subagent; needs a cross-family pin in AGENTS.md model-routing), or `--review=none`. Wall-clock limits and iteration caps belong to the driver (`/goal --tokens`, `/goal` stop clauses, or `/loop` cadence); a pilot tick has no timeout machinery.
