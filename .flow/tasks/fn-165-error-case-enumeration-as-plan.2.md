---
satisfies: [R2, R3, R4, R5, R6]
---
# fn-165-error-case-enumeration-as-plan.2 Skill propagation: plan enumeration, interview probe, worker test-tie, CHANGELOG, mirrors

## Description
Propagate the error-case discipline into the three skill surfaces (plan AC-derivation, interview probe, worker test-tie), run the fixture walkthrough that verifies plan behavior, stage CHANGELOG + docs-site, regenerate codex mirrors.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan/steps.md` (:341-411 scaffold heredoc, :427-433 R-ID rule), `plugins/flow-next/skills/flow-next-plan/SKILL.md` (:226), `plugins/flow-next/skills/flow-next-plan/examples.md`, `plugins/flow-next/skills/flow-next-interview/questions-technical.md` (:67-72 AC bucket), `plugins/flow-next/agents/worker.md` (:279), `CHANGELOG.md`, codex mirror (regenerated)

### Approach
- Plan steps.md: in the R-ID rule block and the scaffold heredoc, instruct enumerating error/invalid/boundary cases per criterion (malformed input, missing files, conflicting state, limits) into the AC bullets, with the "no error surface beyond X" escape; mirror one-liner in SKILL.md:226; one good/bad example pair in examples.md. Note the G-ID rule: discipline applies to spec-added R-IDs only.
- Interview questions-technical.md AC bucket: add the error-surface probe — fire when drafted/existing ACs lack negative cases; accept a one-line "no error surface" answer without escalating.
- worker.md:279: extend the test rule — required tests cover every error case enumerated in the ACs the task satisfies; done summary references them. Specs with none enumerated trigger nothing (not retroactive).
- R2 fixture walkthrough: compose the plan skill's AC step against "parse a config file" and record the derived error-case ACs in this task's done summary as evidence.
- CHANGELOG `## Unreleased` (user-outcome-first). Docs-site (`~/work/flow-next.dev`): update `src/content/docs/specs/writing-specs.mdx` (the spec-writing guide page) for the negative-cases convention NOW; verify `pnpm build`; commit in the docs-site repo (record its SHA in the done summary). The site's versioned changelog + version references defer to the batched release. Downstream walk (same workstream): `~/work/agent-instructions/downstream-properties.md` — recorded update-or-no-change decision for microsite, AIxSDLC guide, vault. `./scripts/sync-codex.sh` twice for this task's skill/worker edits; new Claude-only phrasing gets a transform + guard if the sync guards flag it.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-plan/steps.md:420-440` — R-ID rule block (primary anchor)
- `plugins/flow-next/skills/flow-next-interview/questions-technical.md:20-75` — both buckets (probe goes in AC bucket; general Error Handling bucket at :25-30 stays)
- `plugins/flow-next/agents/worker.md:270-290` — test-writing rule

**Optional**:
- `plugins/flow-next/skills/flow-next-plan/examples.md` — where the example pair fits
- `scripts/sync-codex.sh` — transform/guard patterns

### Key context
- fn-163/fn-164 also edit worker.md (different sections) — second lander rebases.
- Keep additions terse; this spec's own weight-discipline constraint applies to its prose.

### Acceptance
- [ ] Plan skill instructs error-case enumeration at AC derivation; examples.md pair added (R2)
- [ ] Fixture walkthrough evidence ("parse a config file" → error-case ACs) in done summary (R2)
- [ ] Interview probe added to AC bucket with the no-escalation escape (R3)
- [ ] worker.md test-tie landed, scoped to enumerated cases only (R4)
- [ ] CHANGELOG Unreleased; docs-site writing-specs.mdx updated, `pnpm build` green, docs-site commit SHA recorded; versioned site changelog deferred to batched release; downstream update-or-no-change decisions recorded (R6)
- [ ] sync-codex.sh x2 idempotent, mirrors committed, guards green; pinning/budget suites unchanged (R5)
## Acceptance
- Plan/interview/worker prose carries the discipline; fixture walkthrough evidence recorded (R2, R3, R4)
- CHANGELOG + docs-site staged; codex mirrors regenerated twice-idempotent (R5, R6)
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
