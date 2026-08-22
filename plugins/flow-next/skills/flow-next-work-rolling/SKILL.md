---
name: flow-next-work-rolling
description: Rolling-frontier variant of /flow-next:work - admits a new ready task at every worker-return event instead of at wave boundaries, with isolated per-task workspaces, conductor-owned review, and a shared outside-tree notes surface. Triggers on /flow-next:work-rolling with the same inputs as /flow-next:work. User-invoked only - pilot and land never dispatch it. (experimental - can change or disappear)
user-invocable: false
---

# Flow work - rolling frontier (experimental beta)

**This skill is a thin delta over the canonical `flow-next-work` skill.** It replaces exactly one thing: canonical phases.md Phase 3 (the task wave loop) becomes the rolling scheduler in [references/rolling-scheduler.md](references/rolling-scheduler.md). Every other contract - hard requirements, mode parsing, setup questions, input grammar, branch handling, quality phase, ship phase, completion review, tracker gating, guardrails - is consumed from the canonical work skill's files **by pointer**, so a fix to canonical work applies here without a second edit.

**Never fork canonical content.** The canonical work skill's files are read, never copied into this skill and never edited from it. A canonical-work change this skill cannot consume by pointer is a blocking defect of THIS skill's structure, fixed here - never by forking or editing the canonical file (fn-203 R3).

**Experimental.** This beta may change or be replaced as it matures; canonical `/flow-next:work` is unchanged and remains the default.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks (here and in `references/rolling-scheduler.md`) use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Canonical work skill location (same three-rung shape).** This skill reads the canonical `flow-next-work` files by pointer; resolve their directory once and use `$WORK_SKILL` everywhere:

```bash
WORK_SKILL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-work"
[ -f "$WORK_SKILL/SKILL.md" ] || WORK_SKILL="<plugin-root>/skills/flow-next-work"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -f "$WORK_SKILL/SKILL.md" ] || WORK_SKILL="$(dirname "$(dirname "$FLOWCTL")")/skills/flow-next-work"   # derive from the resolved $FLOWCTL (scripts/ sits beside skills/ under the plugin root)
```

If `$WORK_SKILL/SKILL.md` still does not resolve, stop with `NEEDS_HUMAN: canonical flow-next-work skill not found - the beta consumes it by pointer and cannot run without it`.

## Execution contract

1. **Read `$WORK_SKILL/SKILL.md` and follow it in full** - hard requirements (done via `flowctl done` + verified status, `git add -A` staging, green-tree review dispatch), Ralph/autonomous mode rules, input grammar, option parsing, and the setup questions (branch first; review when `REVIEW_BACKEND` is `ASK`). Where that file says "read phases.md", apply step 2 below instead.
2. **Read `$WORK_SKILL/phases.md` and execute it with one substitution**: Phases 1 (resolve input), 2 (branch choice), 4 (quality), and 5 (ship) run exactly as written there. **Phase 3 is replaced**: do NOT execute canonical Phase 3 (3a-3g); instead read [references/rolling-scheduler.md](references/rolling-scheduler.md) and execute it as this run's Phase 3. The scheduler reference re-enters canonical files by pointer where it says so (tracker gates, wave-join mechanics, plan-sync dispatch, completion review gate 3g).
3. **Workers are the canonical `worker` subagent, unchanged.** Every dispatch uses the canonical prompt template and worker.md phases; the scheduler reference fixes the flag values (`PARALLEL_WAVE: true` on every dispatch - review and completion are conductor-owned here for every backend).

## Cross-run claim contention (verified, not assumed)

Task claims live in the shared runtime state store and are spec-scoped, not skill-scoped. A beta run and a canonical `/flow-next:work` run on the same spec contend on the same claims: `flowctl start` on a task claimed by another actor fails (`claimed by '<actor>'`, rc 1 - verified 2026-08-22), and the failed claim drops the task from that run's admissible set (existing semantics, fail closed). Same-actor re-`start` is flowctl's own-task resume, not a second claim - so admission must also treat any task already `in_progress` as in flight elsewhere and never dispatch it. Never clear or steal another run's claim (`--force`/`--reclaim` are human-only repairs).

## Guardrails

- Everything canonical work forbids is forbidden here; its guardrails apply verbatim (read them in step 1).
- **The concurrency cap stays at 3.** Raising it is out of scope for this beta (fn-203 Boundaries).
- **`planSync.enabled=true` disables concurrent admission entirely** - the run degrades to serial, canonical behavior (fail-closed; the scheduler reference carries the gate). **`true` is the shipped default**, so rolling admission has an explicit prerequisite: `flowctl config set planSync.enabled false`. Interactive runs offer that opt-out once when the gate fires; autonomous runs report the unmet prerequisite and never mutate config.
- **Notes-surface content is read by pointer, never embedded** into a dispatch prompt (the scheduler reference carries the rule).
- **Review surfaces are untouched**: reviewer identity, rubric, diff scope, SHIP-before-done gate, and the fix-loop cap are canonical work's, byte-unchanged (fn-203 R5/R8).
