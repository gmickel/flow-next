---
satisfies: [R1, R2, R10, R11, R12, R13]
---

## Description

Build the `/flow-next:map` skill scaffold and the clawpatch detection + init + provider-free map invocation path. This is fn-50's **early proof point** — if the wrap-clawpatch approach can't be built cleanly via skill bash with graceful degradation, the whole opt-in-skill architecture needs reconsideration before fn-50.2-6.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-map/SKILL.md` (new) — frontmatter, preamble, mode detection, ralph-block, install/init/map workflow pointer
- `plugins/flow-next/skills/flow-next-map/workflow.md` (new) — phase-by-phase execution
- `plugins/flow-next/commands/flow-next/map.md` (new) — slash-command shim (13-line pattern from `commands/flow-next/prospect.md`)

## Approach

Mirror the `flow-next-prospect/` skill scaffold (smallest live example with prelude + Ralph-block + workflow pointer pattern) at `plugins/flow-next/skills/flow-next-prospect/SKILL.md:1-89`. Frontmatter shape per `agent_docs/adding-skills.md:5`.

Mirror the `/flow-next:resolve-pr`-wraps-`gh` install-detection pattern at `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md:14-18`. Plain `command -v clawpatch` check + hard-exit-with-message. **No auto-install.**

Use the FLOWCTL prelude consolidation pattern from `agent_docs/adding-skills.md:52-81`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
```

Define `SUPPORTED_CLAWPATCH=">=0.4.0 <0.5.0"` as a single skill-prose constant (R10). Use a tolerant `clawpatch --version` regex `(\d+\.\d+\.\d+)`; outside-range = warn + degrade.

PNPM_HOME pre-flight (R11): when missing-binary branch fires, check `pnpm bin -g` exit-0 vs `command -v clawpatch` divergence; print the pnpm v11 PNPM_HOME hint.

Config-state echo (R12) at skill entry — one four-line block before any work runs.

Ralph-block (R13): hard-error early when `FLOW_RALPH=1` OR `REVIEW_RECEIPT_PATH` set. Mirror `flow-next-capture/SKILL.md` Ralph-block prose. **Decline-to-run only** — the skill MUST NOT write anything to `$REVIEW_RECEIPT_PATH` (that file belongs to the upstream review caller; writing there would corrupt unrelated receipts). One-line stderr diagnostic naming the trigger var (e.g. `/flow-next:map: declines under Ralph (REVIEW_RECEIPT_PATH set); rerun interactively`), then `exit 2`.

Default `clawpatch map` invocation passes `--source heuristic` explicitly — never rely on clawpatch's own default in case upstream changes it. `--source` flag flows through as passthrough.

Write `.clawpatch/.gitignore` skeleton self-contained inside `.clawpatch/` (decision lock-in #1). Skill, NOT flowctl, owns this write (STRATEGY zero-dep — flowctl never references clawpatch).

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md:1-89` — closest scaffold precedent
- `plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md:15-22` + `workflow.md:14-18` — install-detection + graceful-degrade pattern for an external CLI wrap
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` (Ralph-block section) — R13 pattern
- `agent_docs/adding-skills.md` — full skill scaffold convention
- `plugins/flow-next/scripts/flowctl.py:4416-4434` (`_ensure_flow_gitignore`) — pattern reference for the `.gitignore` skeleton write (DO NOT call this helper; replicate the shape in skill bash)

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-prime/SKILL.md` — preamble pattern
- `plugins/flow-next/skills/flow-next-audit/SKILL.md` — alternative larger scaffold

## Key context

- clawpatch CLI is 11 days old, weekly minor releases; pre-1.0. Tolerant version parsing matters.
- `clawpatch init` is fully deterministic. Detects git remote / branch / project name / languages / frameworks; writes `.clawpatch/project.json` + `.clawpatch/config.json`. Does NOT contact any provider. Safe to call automatically.
- `clawpatch map --source heuristic` is provider-free. App.ts:121-126 verified: `provider = source === "heuristic" ? null : ...`.
- Default `--source` is `heuristic` upstream (cli.ts:1925); we still pass it explicitly for stability.

## Acceptance

- [ ] R1: `plugins/flow-next/skills/flow-next-map/SKILL.md` exists with the canonical skill frontmatter + preamble + ralph-block + workflow pointer
- [ ] R1: `command -v clawpatch` + `clawpatch --version` detection in workflow.md; missing-binary branch prints `pnpm add -g clawpatch` verbatim and exits cleanly (no auto-install)
- [ ] R1: Default skill invocation passes `--source heuristic`; `--source` flag flows as passthrough; works without `CLAWPATCH_PROVIDER` configured
- [ ] R2: When `.clawpatch/` absent, skill runs `clawpatch init` first, then writes `.clawpatch/.gitignore` skeleton (self-contained inside `.clawpatch/`)
- [ ] R10: Skill prose contains `SUPPORTED_CLAWPATCH=">=0.4.0 <0.5.0"`; outside-range invocations emit one-line stderr warning and continue
- [ ] R11: Missing-binary branch detects `pnpm bin -g` exit-0 + `command -v clawpatch` exit non-zero and prints PNPM_HOME `bin/` setup hint
- [ ] R12: Skill prints active config state block on entry (clawpatch version, --source, CLAWPATCH_PROVIDER, flow-next review backend, `.clawpatch/` last-mapped or "absent")
- [ ] R13: Skill exits cleanly under Ralph (`FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` set) with non-zero exit + one-line stderr diagnostic naming the trigger var; **no writes to `$REVIEW_RECEIPT_PATH`**; no `AskUserQuestion` blocks fire
- [ ] `plugins/flow-next/commands/flow-next/map.md` slash-command shim exists matching the prospect.md shape
- [ ] Manual smoke: `/flow-next:map` against this repo (where clawpatch is not installed) prints clean install instructions and exits 1

## Done summary

_To be filled by `/flow-next:work` on completion._

## Evidence

_To be filled by `/flow-next:work` on completion._
