---
name: flow-next-features
description: Seed or maintain the committed user-POV feature map at `.flow/features/` so QA and drive reuse how a user reaches each feature. Two state-resolved modes: no `.flow/features/` (or explicit init intent) seeds it; a present map maintains it. Triggers on /flow-next:features, "seed the feature map", "maintain the feature map", "feature map", "init features". Never dispatched by pilot, land, Ralph, or any autonomous driver.
user-invocable: false
allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task
---

# /flow-next:features - compounding user-POV drive knowledge

A committed directory (`.flow/features/`, beside `.flow/memory/`) records, from the user's point of view, what each user-facing feature is, how a user reaches it, how an agent drives it, and which traps waste a verification run. QA and drive stop re-deriving navigation; work can reuse it to verify what it built.

Split that keeps existing contracts intact: **map = how a user gets there (compounds). Spec = what to prove this time. Live drive = proof.**

**Read [seed.md](seed.md) for seed-mode phases.** Feature file shape: [references/feature-entry-contract.md](references/feature-entry-contract.md). Doctor + proof: [references/doctor-and-proof.md](references/doctor-and-proof.md). Maintain (when `MODE=maintain`) executes [maintain.md](maintain.md). If that file is not in this skill directory yet, end `BLOCKED` naming that maintain is not shipped.

There is no flowctl features subcommand. The skill validates the four-H2 shape itself. The only flowctl calls are `memory search` / `memory add` for the `feature-map-drift` tag handoff on the maintain path.

## Preamble

**CRITICAL: flowctl is BUNDLED - NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `maintain.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Inline skill (no `context: fork`)** - `AskUserQuestion` must stay reachable for the few facts seed cannot observe. Subagents cannot call blocking question tools (Claude Code issues #12890, #34592). On portable hosts without `AskUserQuestion`, fall back to a plain-text numbered prompt with a final `Other - type your own answer` option. (sync-codex.sh rewrites AskUserQuestion to a plain-text numbered prompt in the Codex mirror.) For read-only scouts use `Task` with `subagent_type: Explore` (or the host's generic read-only dispatch with Edit/Write disallowed when Explore is unavailable).

## Autonomy refusal

`/flow-next:features` is user-invoked (or a host loop the human started). Pilot, land, Ralph, and every other autonomous driver must not dispatch it. Scan the autonomy-marker **namespace**, never a fixed two-var list. Any hit refuses with the typed one-line report and stops.

```bash
REFUSE=0
# Namespace scan over autonomy marker families. Never a fixed two-var list.
# Families: FLOW_RALPH*, REVIEW_RECEIPT_PATH, any FLOW_*AUTONOM* name,
# plus the mode:autonomous argument token.
if env | grep -E '^(FLOW_RALPH|REVIEW_RECEIPT_PATH)' >/dev/null 2>&1; then
  REFUSE=1
fi
if env | grep -E '^FLOW_[^=]*AUTONOM' >/dev/null 2>&1; then
  REFUSE=1
fi
case " ${ARGUMENTS:-} " in
  *" mode:autonomous "*) REFUSE=1 ;;
esac
if [ "$REFUSE" = "1" ]; then
  echo 'FEATURES_VERDICT=REFUSED features=0 reason="autonomy marker present; /flow-next:features is user-invoked only"'
  exit 2
fi
```

## Mode Detection

State-resolved, cwd-relative to the repo root (`.flow/features/` under the current working directory). No `.flow/features/` directory, or explicit init intent (`--init`, `init`, `mode:seed`, `--seed` in `$ARGUMENTS`), routes to **seed**. A present map with no init intent routes to **maintain**. Consumers elsewhere gate on directory existence only: no config key, no registration.

```bash
MODE="maintain"
if [ ! -d ".flow/features" ]; then
  MODE="seed"
fi
RAW_ARGS="${ARGUMENTS:-}"
for ARG in $RAW_ARGS; do
  case "$ARG" in
    --init|init|mode:seed|--seed) MODE="seed" ;;
  esac
done
printf 'MODE=%s\n' "$MODE"
```

| Mode | When | Behavior |
|------|------|----------|
| **seed** | `.flow/features/` absent, or explicit init intent | Interview the repo, prove each route with one live drive, write the index plus one file per proven feature. See [seed.md](seed.md). |
| **maintain** | `.flow/features/` present and no init intent | Audit-shaped pass over the existing map. See [maintain.md](maintain.md). |

## Interaction Principles

- **Interview the repo, not the user.** Surface, run command, drive mechanism, observable evidence, isolation: read them from the checkout. Ask only what cannot be observed.
- Ask **one question at a time** via `AskUserQuestion` (call `ToolSearch` with `select:AskUserQuestion` first if its schema is not loaded). Fall back to numbered options in plain text only if the tool is unreachable or errors. Never silently skip the question.
- Prefer **multiple choice** when natural options exist. Lead with the recommended option and a one-sentence rationale.
- Do **not** ask before evidence is gathered. Observation first, questions second.
- Multi-surface repos (web + CLI) seed **per-surface feature groups** under one index. Enumeration is observation: each feature file carries `**Surface:**`; consumers select by surface + sub-feature IDs.

## Forbidden

- **Dispatch by an autonomous driver.** Pilot, land, Ralph, or any autonomy-marker hit: refuse. Cadence belongs to the human or their host loop.
- **Editing product code in maintain.** Maintain's edit scope is `.flow/features/` plus harness scripts the map owns. Product bugs are reported and kept out of the PR.
- **Merging.** Never `gh pr merge`, never `/flow-next:land`. A `changed` maintain PR stays open for the human or land.
- **Driving an instance this run did not start.** Doctor names the owner. An orphaned port from a crashed prior run ends `BLOCKED`; reclaim is left to the human. Never kill by process name - kill what this run started.
- **Setting `context: fork`** - blocking-question tools must stay reachable.
- **Duplicating the drive-skill ladder.** Live driving consumes [flow-next-drive](../flow-next-drive/SKILL.md) by pointer. A copy of CDP / agent-browser / Computer-Use actuation detail in this skill has broken this.
- **Writing an undriven feature file.** Nothing enters the map that was not driven once.
- **Treating the map as the intent source.** Specs and acceptance criteria stay the contract of what to prove. The map is how-to-drive only.

## Workflow

1. Run the autonomy-refusal fence. On refuse, the `FEATURES_VERDICT=REFUSED` line is the last line of the run.
2. Run the mode-detection fence. Honor `MODE`.
3. **seed** - execute [seed.md](seed.md) in order.
4. **maintain** - execute [maintain.md](maintain.md) in order. If `maintain.md` is absent, the last line is `FEATURES_VERDICT=BLOCKED features=0 reason="maintain mode not shipped yet"` and the run stops.

## Terminal line

Every run ends with exactly one terminal line, the last line of the response, with nothing after it:

```text
FEATURES_VERDICT=<SEEDED|CLEAN|CHANGED|BLOCKED|REFUSED> features=<n> reason="<one line>"
```

| Verdict | When |
|---------|------|
| `SEEDED` | Seed landed at least one proven feature (partial seed names failures in `reason`) |
| `CLEAN` | Maintain: no map/harness change, no branch, no PR |
| `CHANGED` | Maintain: one PR of proven map/harness corrections only |
| `BLOCKED` | Named blocker (orphaned port, concurrent isolation failure, source-reader collapse of the pass). Next run re-enters fresh. |
| `REFUSED` | Autonomy marker, no drivable surface, no usable driver on this host, or broken checkout |

Use `features=0` when nothing landed. `reason` is one line, quoted.
