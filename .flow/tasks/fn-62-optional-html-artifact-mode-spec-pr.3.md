---
satisfies: [R3, R4, R7, R8, R10]
---

## Description
Wire the spec lens into the two lifecycle touchpoints that change spec state: capture (spec-only rendering) and plan (adds the plan layer). Includes the Lavish session flow, the artifact link-back in the spec markdown, and the executable early proof point for the fn-62.2 disclosure file.

**Size:** M
**Files:** plugins/flow-next/skills/flow-next-capture/workflow.md, plugins/flow-next/skills/flow-next-capture/SKILL.md (footer note), plugins/flow-next/skills/flow-next-plan/steps.md, plugins/flow-next/skills/flow-next-plan/SKILL.md

## Approach
- Gate everywhere: `flowctl config get artifacts.html.enabled` must be checked in an actual bash block, not prose (memory: skill-workflow-snippets-must-enforce). Off/absent ⇒ no reference load, no artifact, no session, no output.
- capture: after Phase 5 write (workflow.md:590 region), when gated on: load plugins/flow-next/references/html-artifacts.md, generate `.flow/artifacts/<spec-id>/spec.html` (spec-only — no tasks yet), add an artifact link line near the top of the spec md (R10), surface "artifact written → <path>" in the Phase 6 footer.
- plan: generate AFTER the Step 8 refinement loop EXITS (user picked 1/2/3), not on first arrival at Step 8 — Step 8's go-deeper/simplify options mutate tasks and would stale the lens; if a Step 8 mutation happens after generation, regenerate before the final footer. Same fixed path, now WITH the plan layer (task DAG + R-ID coverage matrix — state-dependent, one pathway).
- Artifact link idempotency: the link line in spec md uses a recognizable marker; regeneration REPLACES the existing line in place — never appends a duplicate across repeated capture/plan runs.
- Lavish flow (interactive only): if `command -v lavish-axi` → open session + background poll per the reference file; annotations map to spec-markdown edits then regenerate. Autonomous (mode:autonomous / FLOW_AUTONOMOUS / Ralph): generate-only, NEVER open/poll; one stderr line at most.
- Link strategy: artifacts committed by default → repo-relative link in spec md; if `git check-ignore .flow/artifacts/` hits → local-open guidance line instead.
- Staleness stamp + fixed-path rules come from the reference file — the skill prose cites it, never duplicates the design rules inline (token discipline).

## Investigation targets
**Required:**
- plugins/flow-next/skills/flow-next-capture/workflow.md:580-640 (Phase 5) + :830-900 (Phase 6 footer)
- plugins/flow-next/skills/flow-next-plan/steps.md:493-558 (validate → Step 8 loop → exit options)
- plugins/flow-next/references/html-artifacts.md (from fn-62.2)
**Optional:**
- plugins/flow-next/skills/flow-next-qa/SKILL.md:86-87 — cross-skill reference citation shape

## Acceptance
- [ ] Mode off: capture + plan load no reference file, write no artifacts, open no sessions, produce no artifact-related output (R1 regression)
- [ ] Mode on, capture: spec.html generated at the fixed path, spec-only rendering, link line in spec md, footer mentions the path
- [ ] Mode on, plan: same file regenerated WITH task DAG + R-ID matrix, generated only after the Step 8 loop exits; a Step 8 mutation after generation triggers regeneration before the final footer
- [ ] Repeated capture/plan runs leave exactly ONE artifact link line in the spec md (replaced in place, never duplicated)
- [ ] EARLY PROOF executed here: a fresh session given ONLY the fn-62.2 reference file regenerates fn-62's spec artifact in house style — zero external requests (reference self-check grep), layered DAG, provenance chips, staleness stamp — matching the validated smoke artifacts in quality
- [ ] Lavish present + interactive: session opens, background poll runs; autonomous run generates but never polls (grep transcript for poll)
- [ ] Ignored-artifacts repo gets local-open guidance, no dead repo link

## Done summary
Retroactive tidy (2026-08-04): the feature this task describes shipped long ago but the task record was never closed when the parent spec closed — surfaced by the closed-parent orphan rule in `flowctl brief` (3.15.0). Evidence of existence: capture/plan render-lens touchpoints shipped (plan Step 8.5 html-render-lens reference is live). No new work performed; this receipt closes the stale record.
## Evidence
- Commits:
- Tests:
- PRs: