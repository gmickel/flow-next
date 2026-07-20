---
satisfies: [R3, R4, R5, R6, R7]
---

## Description

The skill-prose half: consume the new plumbing and consolidate fences. Prose-only; behavior contracts preserved.

**Size:** L (six skills; mechanical once .1's JSON shapes are fixed)
**Files:** plugins/flow-next/skills/flow-next-land/workflow.md, flow-next-plan/steps.md (+SKILL.md if reads move), flow-next-pilot/SKILL.md+workflow.md, flow-next-make-pr/workflow.md, flow-next-impl-review/SKILL.md, flow-next-plan-review/SKILL.md+workflow.md, plugins/flow-next/codex/ (regenerated mirror)

## Approach

Per the spec Approach item 3, with these hard rules:
- land: cfg() -> one `config get land --json` capture + jq lookups. Keep the null-tolerant defaults exactly (the CLEAN_REVIEW_PATTERN ""-vs-null contract is subtle - preserve it).
- plan: <=2 config reads; `spec create --branch` (drop set-branch call); `task create --description-file/--acceptance-file` where no satisfies-frontmatter needed (set-spec --file stays for frontmatter tasks - state the split in prose once).
- pilot: RE-SCOUT FIRST (structure changed since fn-101: references/backlog-mode.md extraction). Consolidate the tick's config reads to one subtree read; dedup hard guards only if still duplicated; never inline backlog-mode.md.
- make-pr: Phase 0 -> <=3 read fences, §0.5 tasks-done semantics intact.
- impl-review: 3 arg-parse fences (SKILL.md L155/175/219) -> 1.
- plan-review: single-source the per-backend block; PRESERVE VERBATIM the Foreground rule (SKILL.md:124) and fn-90 cap prose (L263) - diff-check both after the edit.
- sync-codex.sh TWICE, commit the mirror with the canonical change; validation guards must stay green; portable-host clauses for anything Claude-only.

## Investigation targets

**Required:**
- The exact JSON shapes .1 shipped (read its tests)
- pilot SKILL.md + workflow.md + references/backlog-mode.md CURRENT structure (fresh scout - do not trust fn-101 line anchors)
- land/workflow.md:53-72 cfg() + its consumers

## Acceptance

- [ ] land Phase 0: exactly 1 config invocation (R3)
- [ ] plan 4-task dry-run: >=40% fewer flowctl invocations vs pre-change count (scripted before/after count in evidence) (R4)
- [ ] pilot: 1 subtree read per tick; re-scout summary recorded in the commit/evidence; backlog-mode split respected (R5)
- [ ] make-pr <=3 fences; impl-review 1 arg fence; plan-review single-sourced with Foreground + cap prose byte-preserved (R6)
- [ ] sync-codex x2 idempotent, mirror committed; smoke + unittest green (R7)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
