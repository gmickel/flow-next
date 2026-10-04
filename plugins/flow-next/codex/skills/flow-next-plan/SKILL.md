---
name: flow-next-plan
description: Plan a feature into a flow-next spec with tasks in .flow/. Use when asked to plan, spec out, or break down work (fn-N ids).
user-invocable: false
---

# Flow plan

Turn an idea or an existing spec into a spec with right-sized tasks in `.flow/`, grounded in repo research. Plan writes no code.

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step of this skill.

**`.flow/` is the only task tracker.** Every spec and task is created or changed through `flowctl`. A markdown TODO list, a TodoWrite call, or a plan file kept outside `.flow/` as the record has broken this.

## Preamble

**flowctl is bundled, not installed globally** (`which flowctl` fails). Define it once; later blocks here and in `steps.md` use `$FLOWCTL`:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

Check once for flowctl copies left by an older install layout:

```bash
LEFTOVERS=""
for p in .flow/bin/flowctl .flow/bin/flowctl.cmd .flow/bin/flowctl.py \
         .flow/bin/flowctl_bootstrap.py .flow/bin/flowctl-help.txt \
         .flow/bin/flowctl_tracker .flow/templates/spec.md .flow/usage.md; do
  [ -e "$p" ] && LEFTOVERS="${LEFTOVERS}${p}"$'\n' || true
done   # || true: an empty LEFTOVERS (the normal case) must read as success
```

None present: say nothing. Any present: print one line saying nothing reads them and they can be deleted by hand or by `/flow-next:setup`, then continue. Never ask, stop, or delete here.

## No implementation code

The spec states what and why as contracts; each task states how: named files, the repo pattern to follow (`file:line`), ordering, and non-obvious gotchas. Code in a plan is limited to signatures and interfaces, pointers to existing patterns, a recent or surprising API from docs-scout, and a gotcha from practice-scout. A full function or module body, or a copy-paste block over about 10 lines, has broken this: implementation happens in `/flow-next:work` with fresh context, and code written here is paid for again there and drifts.

## Input

Full request: $ARGUMENTS

Accepts a freeform idea; a spec id `fn-N-slug` (legacy `fn-N`, `fn-N-xxx`); a task id `fn-N-slug.M` (legacy `fn-N.M`, `fn-N-xxx.M`); a tracker handle such as `wor-17` that `flowctl show` resolves (always the existing spec or task, never a new idea; see Step 1); and chained instructions such as "then review with /flow-next:plan-review".

Empty input: ask "What should I plan? Give me the feature or bug in 1-5 sentences." Under autonomy, report `NEEDS_HUMAN: no planning input provided` and stop.

A ready or captured spec is plan input. An unshaped, oversized idea with several consequential unknowns is not: recommend `/flow-next:chart` (or `/flow-next:flow --explain` when unsure) and stop. Plan decomposes understood work; it does not replace discovery.

## Options

**Autonomy.** The literal token `mode:autonomous` in `$ARGUMENTS` (strip it) or `FLOW_AUTONOMOUS=1` sets `AUTONOMOUS=1`. Then no question is ever asked: explicit flags win, and anything unset takes its default (depth below, research `repo-scout`, review the configured backend, `none` when it is `ASK`). A genuinely unanswerable ambiguity stops with a one-line `NEEDS_HUMAN: <reason>`.

**Depth.** `--depth=short` ("quick", "minimal"), `--depth=standard` ("normal"), `--depth=deep` ("comprehensive", "detailed"). Default SHORT. Depth picks the scout set (Step 1) and the spec sections (Step 4).

**Research.** Always `repo-scout`; `--research=grep` is a no-op and any other value is ignored.

**Review.** `--review=codex` ("review with codex", "codex review", "use codex"), `--review=host` ("host review", "use host": the host-native fresh-context reviewer), `--review=none` or `--no-review` ("no review", "skip review"). `--review=rp` and `--review=export` were removed: say "RepoPrompt review (rp, export) was removed in flow-next 8.0.0; review backends: claude, codex, copilot, cursor, host." once and treat review as nothing configured (`ASK`, below).

Initialize and capture one preflight snapshot before routing or scouting (also under autonomy), from the repository root (never this skill's directory, where flowctl finds no config). Every later config read uses this literal path:

```bash
$FLOWCTL init --json
PLAN_CFG="${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json"
$FLOWCTL preflight --json > "$PLAN_CFG" 2>/dev/null || printf '{"key":null,"value":{}}' > "$PLAN_CFG"
```

Plan asks no setup question: flags win, depth takes its default, and review uses the configured
backend from the snapshot (`.probes.review_backend.value.backend`). When that reads `ASK` (nothing
configured), review is `none` and the handoff says once "no review backend set; run setup or set
review.backend". Show the hint:

```
(Tip: --depth=short|standard|deep, --review=codex|copilot|cursor|claude|host|none)
```

## Workflow

Read [steps.md](steps.md) and follow each step in order. Its optional paths (readiness warning, Route A, tracker-first mint, tracker projection, review, next-steps menu) load their references only when the step's condition holds.

**Step 1 launches every scout in the depth-appropriate set as parallel multi-agent threads (Codex spawns them concurrently).** A plan whose research skipped a scout in its tier, or ran the set sequentially, has broken this.

## Output

- Spec: `.flow/specs/<spec-id>.json` + `.md`; tasks: `.flow/tasks/<spec-id>.M.json` + `.md`.
- No code changes. Specs and tasks live in `.flow/`; temporary drafts (the `/tmp` bodies steps.md writes) are fine.
