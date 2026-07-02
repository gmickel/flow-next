---
satisfies: [R3, R4, R5, R6, R7, R12, R13]
---

## Description

Mechanical round-trip eliminations across plan, deps, make-pr, tracker-sync, plus the plan/work/resolve-pr config-get sweep and prime's scout-model prose fix. Theme: "never re-fetch or re-emit what this run already has". CANONICAL FILES ONLY — mirror regen is fn-81.4's. Depends on fn-81.1.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan/steps.md`, `plugins/flow-next/skills/flow-next-deps/SKILL.md`, `plugins/flow-next/skills/flow-next-make-pr/workflow.md`, `plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md` (+`steps.md` call sites), `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md`, `plugins/flow-next/skills/flow-next-prime/{SKILL.md,workflow.md}`

## Approach

- plan steps.md: capture `SHOW_JSON` once at the Step 1 context fetch (:70) and reuse for the readiness read (:77); delete Step 5 item 8 "Output current state" (:487-491). KEEP the Step 7 fix-loop re-anchor (:528,:536; compaction-justified). Verify pilot judges plan by flowctl state, not this stdout (grep pilot workflow; record in summary). ALSO fix plan's own Step 6.5 double-get (`steps.md:506-508` reads `tracker.perEvent.plan` twice) → `LEAF=` single-fetch.
- deps SKILL.md: Step 2 (:52-54) and Step 3 (:82-84) byte-identical loops — gather once (Step 2 form), reuse in Step 3 (same bash block, or cache to a unique temp file).
- make-pr workflow.md §4.6b (:1558-1572): keep the guard's PURPOSE (hand-rolled `gh pr create` bypass — comment :1550-1557); happy path asserts locally (grep `$REF` in `$BODY_FILE`) and skips the `gh pr view --json body` refetch; live refetch fires only when the local append demonstrably didn't run.
- tracker-sync body-merge.md:264-273: `set-merge-base --flow-file .flow/specs/<id>.md` (written at :267) instead of re-emitted `/tmp/merged-flow.md`; tracker half keeps a unique temp file; sweep steps.md call sites (:296,:334,:380).
- config-get single-fetch (canonical: work SKILL.md:184-190): fix work phases.md:211-212, :303-304, :423-425 and resolve-pr workflow.md:422-423; final sweep `grep -rn 'config get tracker.perEvent' plugins/flow-next/skills/` — every gate single-fetch.
- prime: re-verify model split against `plugins/flow-next/agents/*.md` frontmatter (expected 7 haiku / 2 sonnet: claude-md, docs-gap); fix SKILL.md:88, :137 header, workflow.md:5.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-plan/steps.md:60-95,480-540,500-520`
- `plugins/flow-next/skills/flow-next-deps/SKILL.md:25-90`
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:1500-1590`
- `plugins/flow-next/skills/flow-next-tracker-sync/references/body-merge.md:255-280`
- `plugins/flow-next/skills/flow-next-pilot/workflow.md` — confirm no dependence on plan's post-write stdout

**Optional:**
- `plugins/flow-next/agents/` frontmatter — prime model ground truth
- `plugins/flow-next/skills/flow-next-work/SKILL.md:184-190` — canonical LEAF gating predicate

## Key context

Do NOT touch: land workflow.md:473 (deliberate fresh probe, fn-66 R3), pilot's dual `gh pr list`, plan's Step 7 re-anchor. fn-82 touches different tracker-sync files (adapter refs) — keep tracker-sync delta minimal.

## Acceptance

- [ ] plan: one `show --json` in Step 1, no post-write show/cat, re-anchor intact, Step 6.5 single-fetch, pilot-dependency check recorded
- [ ] deps: one heavy per-spec loop total
- [ ] make-pr: happy path has no live-body refetch; bypass case still guarded; local grep assertion present
- [ ] tracker-sync: `--flow-file` points at the spec file; no `/tmp/merged-flow.md`
- [ ] `grep -rn 'config get tracker.perEvent' plugins/flow-next/skills/` — every gate single-fetch
- [ ] prime prose matches verified frontmatter split
- [ ] canonical-only diff (no mirror commit)

## Done summary
Round-trip eliminations across plan (single show --json + post-write show/cat deleted; pilot verified state-based), deps (one heavy per-spec gather cached to a unique file), make-pr §4.6b (local ref assertion; live refetch only on the hand-rolled-create bypass), tracker-sync (set-merge-base --flow-file = the spec file itself; tracker half + merge log on unique temps), the tracker.perEvent config-get single-fetch sweep (work x3, resolve-pr, interview, plan Step 6.5 — every gate now uses the canonical LEAF pattern), prime scout-model prose corrected to the verified 7-haiku/2-sonnet split, and R13 fixed-path cleanup (plan + flow-next/SKILL.md /tmp/desc.md-style shared paths → unique per-task paths). Canonical files only; mirror regen deferred to fn-81.4. RP review: SHIP (first pass, 0 findings).
## Evidence
- Commits: 041bab303de86ad00a9ab0b5e0f1f0e08930369e
- Tests: uv run --with pytest python3 -m pytest plugins/flow-next/tests/ -q (1393 passed, 2 skipped, 164 subtests), bash scripts/sync-codex.sh (parity guards pass; mirror output stashed, committed in fn-81.4), grep -rn 'config get tracker.perEvent' plugins/flow-next/skills/ (all gates single-fetch), fixed temp-path greps clean (/tmp/desc.md /tmp/acc.md /tmp/merged-flow.md /tmp/merges.json etc.)
- PRs: