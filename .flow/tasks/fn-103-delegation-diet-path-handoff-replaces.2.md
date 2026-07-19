---
satisfies: [R4, R5, R6, R7]
---

## Description

Docs reframe, the plan-side density sentence, the decision record, CHANGELOG.

**Size:** S
**Files:** `plugins/flow-next/docs/orchestration.md`, `plugins/flow-next/skills/flow-next-setup/templates/usage.md` (the CANONICAL source - never edit .flow/usage.md directly), `plugins/flow-next/skills/flow-next-plan/steps.md`, `.flow/memory/knowledge/decisions/composed-brief-deleted-path-handoff-2026-07-19.md` (new), `CHANGELOG.md`, codex mirror (regen)

1. orchestration.md: reframe the delegation section - the RAW codex-exec bridge is the interactive route; `delegate:codex` = the same bridge with deterministic rails for unattended loops; prompt = fixed path-handoff template (task/spec files ARE the brief). Light touch - the existing host-retains-judgment framing (L59-71) survives.
2. setup templates/usage.md § Orchestration: same reframe in the "flow-next shortcuts" block; verify the bridge recipes need no change (they are already raw-bridge-first).
3. plan steps.md (~L445-485 task template): ONE sentence - task files must carry the full contract (named files, named test cases, named acceptance) because downstream executors receive the task file AS the brief.
4. Decision record per docs/memory-schema.md frontmatter (title, date, track: knowledge, category: decisions, module: skills/flow-next-work/references/codex-delegation.md, tags, applies_when) + alternatives considered (composed brief / path-handoff / mechanical bundle) + the eval results table + do-not-rebuild-without-new-evidence prevention clause + scratchpad harness path.
5. CHANGELOG `## Unreleased` entry (batched, no bump.sh).
6. sync-codex x2 idempotent, guards green (docs are not mirrored; the steps.md edit IS - verify).

## Acceptance
- [ ] R4: both doc surfaces reframed; no composed-brief prescription anywhere
- [ ] R5 (plan side): density sentence in the task-authoring step
- [ ] R6: decision record schema-compliant with alternatives + eval table + prevention clause
- [ ] R7: mirror idempotent, guards green; no version bump

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
