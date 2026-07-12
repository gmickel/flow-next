---
name: flow-next-pilot
description: Single-tick autonomous build-loop conductor for host drivers (/loop, /goal). Each invocation advances exactly ONE ready spec by ONE pipeline stage (plan, plan-review, work, qa [opt-in, gated on pipeline.qa==on], make-pr) and ends with a terminal PILOT_VERDICT line for the driver to read. Triggers on /flow-next:pilot, optionally with --spec <id>, --dry-run, --review=<backend>, --research=<grep|rp>, --depth=<level>. Autonomous by design — never asks the user questions; reports NEEDS_HUMAN instead.
user-invocable: false
allowed-tools: Read, Bash, Grep, Glob, Write, Edit, Skill
---

# /flow-next:pilot — single-tick autonomous build-loop conductor

A tick is one invocation of `/flow-next:pilot`: select one ready spec, classify its current stage (`plan`, `plan-review`, `work`, the opt-in `qa`, `make-pr`), dispatch exactly one existing stage skill, verify state advanced, and end with one terminal `PILOT_VERDICT` line. It is intentionally not a runner; `/loop` in Claude Code or `/goal` in Claude Code / Codex owns repeated invocation.

Pilot and Ralph are alternative autonomous drivers. Ralph is an external shell loop with receipt plumbing; pilot is an in-session conductor for host loop primitives. Never nest them, and never reuse Ralph harness state inside pilot.

Human judgment lives before pilot: the spec content, `depends_on_epics`, and the fn-58 `ready` gate are the consent boundary. Pilot executes the mechanical pipeline one stage at a time, with ambiguity reported as `NEEDS_HUMAN`.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `workflow.md`) use `$FLOWCTL`. Subagents that run in fresh context fall back to the repo-local copy:

```bash
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Pre-check: Local setup version

Non-blocking, never asks (autonomous). On mismatch, stash a `SETUP_STALE` line so the verdict contract can co-locate it with the terminal `PILOT_VERDICT` (a stderr echo alone gets buried); `version_ack` never suppresses it. Detection logic is unchanged:

```bash
[[ -d .flow/tmp ]] && rm -f .flow/tmp/setup_stale 2>/dev/null
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
 mkdir -p .flow/tmp 2>/dev/null
 echo "SETUP_STALE: local v${SETUP_VER}, plugin v${PLUGIN_VER}, run /flow-next:setup" | tee .flow/tmp/setup_stale >&2
fi
```

Continue regardless (never blocks; fail-open - silent when setup was never run, versions match, or any read fails). See the verdict contract for how the stashed line is emitted before the terminal verdict.

## Hard guards (before anything else)

Run these guards before selection, ledger writes, branch changes, or skill dispatch.

```bash
if [[ -n "${FLOW_RALPH:-}" || -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
 echo "Ralph and pilot are alternative drivers — never nest them" >&2
 [[ -f .flow/tmp/setup_stale ]] && cat .flow/tmp/setup_stale
 echo 'PILOT_VERDICT=NEEDS_HUMAN spec=- stage=- reason="nested under Ralph harness (FLOW_RALPH/REVIEW_RECEIPT_PATH set) — refuse to run"'
 exit 1
fi

if git status --porcelain | grep -v '^.. \.flow/' >/dev/null; then
 [[ -f .flow/tmp/setup_stale ]] && cat .flow/tmp/setup_stale
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
PILOT_BACKLOG_OVERRIDE="" # "" = use config; "1" = force backlog (--backlog/--auto)

PREV=""
for ARG in $RAW_ARGS; do
 case "$PREV" in
 --spec) PILOT_SPEC="$ARG"; PREV=""; continue ;;
 --review) PILOT_REVIEW="$ARG"; PREV=""; continue ;;
 --research) PILOT_RESEARCH="$ARG"; PREV=""; continue ;;
 --depth) PILOT_DEPTH="$ARG"; PREV=""; continue ;;
 esac
 case "$ARG" in
 --spec|--review|--research|--depth) PREV="$ARG" ;;
 --spec=*) PILOT_SPEC="${ARG#--spec=}" ;;
 --dry-run) PILOT_DRY_RUN=1 ;;
 --backlog|--auto) PILOT_BACKLOG_OVERRIDE=1 ;;
 --review=*) PILOT_REVIEW="${ARG#--review=}" ;;
 --research=*) PILOT_RESEARCH="${ARG#--research=}" ;;
 --depth=*) PILOT_DEPTH="${ARG#--depth=}" ;;
 -*) echo "Unknown flag: $ARG (ignored by /flow-next:pilot)" >&2 ;;
 *) echo "Unknown argument: $ARG (ignored by /flow-next:pilot)" >&2 ;;
 esac
done
[[ -n "$PREV" ]] && echo "Flag $PREV given without a value (ignored by /flow-next:pilot)" >&2
export PILOT_SPEC PILOT_DRY_RUN PILOT_REVIEW PILOT_RESEARCH PILOT_DEPTH PILOT_BACKLOG_OVERRIDE
```

No branch flag exists in v1. Branch resolution is pilot-owned from the selected spec's `branch_name`.

### Autonomy mode resolution (R1) — gate the wide backlog behavior

Resolve `PILOT_AUTONOMY` once, here, so every downstream block keys off a single value. The gate is a **strict scalar string-enum** — backlog mode activates **only** on the literal `backlog` (config `pilot.autonomy`), or when the per-run `--backlog` / `--auto` flag forced the override. Any other config value (`ready`, `null`, a coerced bool `true`, a typo) leaves pilot in `ready` mode — **byte-for-byte unchanged behavior** (the `references/backlog-mode.md` file is never even read):

```bash
PILOT_AUTONOMY="$($FLOWCTL config get pilot.autonomy --json | jq -r '.value')"
if [ "$PILOT_BACKLOG_OVERRIDE" = "1" ]; then
 PILOT_AUTONOMY="backlog" # --backlog / --auto forces backlog this run
elif [ "$PILOT_AUTONOMY" != "backlog" ]; then
 PILOT_AUTONOMY="ready" # ONLY the literal `backlog` enables — never bool true / typos / null
fi
export PILOT_AUTONOMY
```

When `PILOT_AUTONOMY=ready` (the default), pilot behaves exactly as documented in `workflow.md` Phases 1–6 — no backlog-mode code path runs, `references/backlog-mode.md` is not loaded, and the verdict grammar/stage set/forbidden block are unchanged. When `PILOT_AUTONOMY=backlog`, the SELECT and TRIAGE/ASK phases follow `references/backlog-mode.md` (loaded only then), the verdict grammar gains `ASKED`, and the safety invariants below are active. `FLOW_AUTONOMOUS=1` is exported into every sub-skill / tracker-sync dispatch so the whole tick runs unattended (`plain-text numbered prompt` is never reached).

## The verdict contract (read this before the workflow)

The `/goal` validator is transcript-blind: it reads conversation output only and never runs tools. Every tick therefore echoes its verification evidence into the output: flowctl status fields, task counts, task status transitions, and the gh-confirmed PR URL for make-pr.

Every tick ends with exactly one terminal line, the last line of the response, with nothing after it:

```text
PILOT_VERDICT=<ADVANCED|ASKED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"
```

Use `spec=-` and `stage=-` when no spec was selected. Stage values are exactly `plan`, `plan-review`, `work`, `qa` (opt-in — only when `pipeline.qa==on`), `make-pr`, `land`, plus `triage`/`ask` (backlog mode only), or `-`.

**SETUP_STALE line.** Whenever the pre-check detected a setup-version mismatch it wrote `.flow/tmp/setup_stale`. At EVERY terminal `PILOT_VERDICT` emission - the Phase 6 line and each hard-guard exit - first print that file's `SETUP_STALE: local v<X>, plugin v<Y>, run /flow-next:setup` line, so it lands in the same output block immediately before the verdict and survives into driver logs. Emit it verbatim (`cat .flow/tmp/setup_stale` in bash blocks; a plain preceding line when the verdict is printed as text). It never blocks, is never suppressed, and fail-opens to nothing when the file is absent.

`DEFERRED_TO_LAND` is a distinct *non-terminal-work* verdict (stage `land`): every remaining all-done candidate has an open PR that land — not pilot — owns. It is deliberately separated from `NO_WORK` so a driver can route it to `/flow-next:land` instead of stopping; an all-done spec with an open PR is real outstanding work, never absence of work.

### Backlog-mode verdict grammar (R10 — only when `PILOT_AUTONOMY=backlog`)

Backlog mode **ADDS** `ASKED` and reuses the existing terminals; it changes none of them:

- **`ASKED <id> (<n>)`** — a **durable park**. The `ask` stage wrote a `status=open` question anchor (spec `## Open Questions` for a spec-backed item, or the tracker comment alone for a tracker-only item), so the next tick's SELECT skips this subject. `<n>` is the count of open questions surfaced. Stage = `ask`.
- **`ADVANCED <id> <stage>`** and **`BLOCKED <id> by <dep>`** — reused unchanged (BLOCKED here = ready-but-dep-unsatisfied, a state-changing surface of the dep wait).
- **`NO_WORK` and `DEFERRED_TO_LAND` are kept VERBATIM** — drivers grep `DEFERRED_TO_LAND` to route an all-done-with-open-PR spec to `/flow-next:land`, and `/goal`/`/loop` stop-clauses key on `NO_WORK`; coalescing either into a generic "idle" would break the land hand-off and the loop-stop. Never rename them.
- **No `PROMOTED` verb** — the agent never sets the ready flag; promotion is the human's board act.

**`TRIAGED <id> <class>` is DIAGNOSTIC / dry-run ONLY** — emitted only under a triage-only inspection (`--dry-run`). The split is explicit:

- **Live backlog grammar** (no `--dry-run`): `ADVANCED | ASKED | NO_WORK | DEFERRED_TO_LAND | BLOCKED | NEEDS_HUMAN` — **`TRIAGED` is NOT a live terminal.** A live triage always resolves to a state-changing terminal, so an item can never re-select forever. A live tick MUST NOT end on a bare `TRIAGED` no-op line. The primary grammar line above (which `/loop`/`/goal` drivers read) is exactly this live set.
- **Dry-run-only grammar** (`--dry-run`): adds `TRIAGED <id> <class>` as the diagnostic terminal — the tick classifies and stops, dispatching nothing and parking nothing. A `/loop`/`/goal` driver never runs `--dry-run`, so it never sees `TRIAGED`.

Driver condition examples:

```text
/goal keep running /flow-next:pilot until it prints PILOT_VERDICT=NO_WORK, or stop after 20 turns
/goal keep running /flow-next:pilot --review=codex until PILOT_VERDICT=NO_WORK or PILOT_VERDICT=NEEDS_HUMAN
```

## Forbidden

- Asking the user anything in the tick path. Pilot is autonomous; ambiguity maps to `NEEDS_HUMAN`. In backlog mode, ambiguity that needs a person is surfaced **async** via the `ask` stage (`ASKED`) — never an interactive `plain-text numbered prompt`.
- Dispatching any skill outside the stage set `{plan, plan-review, work, make-pr}` — plus `qa` **only when `pipeline.qa==on`** (fn-72: an opt-in, gate-reversed stage at the all-done juncture before make-pr; with the gate off, `qa` is forbidden and the stage set is byte-for-byte unchanged). **Backlog mode (`PILOT_AUTONOMY=backlog`) additionally invokes `/flow-next:tracker-sync` for the `reconcile` / `list-open` / `list-relations` / `question` ops** — these are read/surface-only tracker calls (`list-relations` is the per-issue dependency-relation READ for dep-ordering), not a pipeline stage, and run only on the backlog path. Capture, interview, resolve-pr, merge, and release are **never** pilot stages — they stay forbidden for their distinct reasons (capture/interview are human authoring upstream of the consent boundary; resolve-pr/merge/release are land's territory downstream of the PR). Opening `qa` under its gate or `tracker-sync` under backlog mode is not a precedent to open any of those five.
- Re-implementing sub-skill logic. Pilot owns selection, dispatch, verification, verdicts, and the strikes ledger only. The backlog-mode SELECT/TRIAGE/ASK workflow lives in `references/backlog-mode.md` (loaded only when `PILOT_AUTONOMY=backlog`); the question-anchor authoring + answer round-trip live in tracker-sync — backlog mode invokes them, never re-implements them.
- **Never merging / never invoking land** (R6) — in either mode, the terminus is `make-pr` (draft). Merge stays human-gated. Backlog mode never calls `/flow-next:land`, `gh pr merge`, or any merge path.
- **Never authoring a spec** (backlog mode) — `capture`/`interview` are human-gated upstream. A missing/too-thin spec is surfaced as a "needs capture/interview" gap and parked (`ASKED`), never auto-written. The only writing the `ask` stage may do is fill an obvious blank in an *existing* spec — never create a spec stub from a bare ticket.
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

**Backlog mode (`PILOT_AUTONOMY=backlog`).** When the autonomy gate resolved to `backlog`, the SELECT and TRIAGE/ASK behavior follows [references/backlog-mode.md](references/backlog-mode.md) — the agentic floor scheduler (loaded **only** in this mode). It widens SELECT (pull-before-scan, union tracker-only items, dep-order, skip parked) and adds the `triage`/`ask` stages **in front of** CLASSIFY; a **workable** item flows into the existing `classify → branch → dispatch → verify` path unchanged. `workflow.md` Phase 0.5 resolves the mode and routes; `workflow.md` Phase 1.5/Phase 3.5 carry the backlog SELECT + TRIAGE/ASK hooks and the safety invariants. The single-tick contract is unchanged: one item, one stage or one durable park, one terminal verdict.

## Unattended runs — rp caveat

The `rp` review backend runs headlessly via rp-cli — it only needs the Repo Prompt app running on the same Mac (cold start: `open -ga "Repo Prompt"`, MCP responds within seconds; a stopped app fails FAST with a clear error, never a hang). For machines without the app (remote/CI), use `--review=codex`, `--review=copilot`, or `--review=none`. Wall-clock limits and iteration caps belong to the driver (`/goal --tokens`, `/goal` stop clauses, or `/loop` cadence); a pilot tick has no timeout machinery.
