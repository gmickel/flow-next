---
satisfies: [R1, R2, R9]
---

## Description

Move default-OFF machinery behind gated references in work and pilot — the spec's early proof point for the gated-reference pattern (forcing sentinel, fail-open, one-level-deep link, mirror auto-copy). Also dedupe pilot's backlog-mode prose and work's delegation value-check. CANONICAL FILES ONLY (mirror = fn-82.5); may run sync-codex locally to validate, not commit.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/{SKILL.md,phases.md,references/tracker-touchpoints.md(new)}`, `plugins/flow-next/skills/flow-next-pilot/{workflow.md,references/qa-stage.md(new)}`

## Approach

- **Gate shape to copy verbatim in spirit:** pilot backlog gate (`flow-next-pilot/workflow.md:58-105` — default branch is a bare `:` no-op, reference never loaded) and work delegation gate (`flow-next-work/phases.md:29-61` — cheap short-circuit + `.flow`-missing guard fails safe).
- **work:** create `references/tracker-touchpoints.md` (with TOC if >100 lines) holding: SKILL.md's bridge overview prose (:170-197 minus the R16 handle-recognition + unlink paragraphs, which STAY), and the three touchpoint blocks (phases.md 3b.1 :207-222, 3d.1 :299-314, 3g's completionReview block). The inline sites shrink to: the shared gating predicate + the spec's EXACT gate skeleton (probe error ⇒ `ACTIVE=1` via `|| ACTIVE=1` on BOTH probe and parse, NO `| jq` pipelines inside the gate — capture raw first, parse separately; sentinel `GATE ACTIVE — STOP. Read references/tracker-touchpoints.md#<section> before continuing.`; default branch bare no-op with no read path; imperative repeated in the prose right after the gate). **DO NOT MOVE:** Phase 5 sync-check + retro-fire + the mandatory 4-state `Tracker sync:` summary template (phases.md:500-550) — inline, byte-preserved (it is the safety net + a shared contract per docs/tracker-sync.md:119). Dedupe delegation value-check: SKILL.md:199-212 ≡ phases.md:29-61 → keep the executable block in phases.md Phase 0 (its consumption site), SKILL.md keeps a one-line pointer.
- **pilot:** create `references/qa-stage.md` holding ONLY the QA-freshness probe (workflow.md "### QA-stage freshness probe" :340-375). Inline remains: the QA_STAGE_ENABLED gate (:317-321) rebuilt on the spec's exact gate skeleton (fail-open, STOP-imperative sentinel naming references/qa-stage.md#probe), the classification rows that CONSUME QA_FRESH (:334, :392 — unchanged), all branch-matrix/dispatch tables (:415-439), and every Phase 5/6 qa reference (:500-541, :621). The reference documents the QA_FRESH computation contract (inputs → the determination the inline rows read).
- **backlog dedupe (same file, same task to avoid overlap):** workflow.md:155-296 and :565-602 restate select/triage/ask that backlog-mode.md:260-266/:324-337 owns — keep enforcing bash, invariants, and `assert_*` inline; delegate the prose mechanics with a one-line pointer per phase. Before deleting any prose line, grep the surviving bash for vars that prose defined (no stranded reads).
- Local `bash scripts/sync-codex.sh` validation: confirm the new references/ files land in the mirror (wholesale dir copy, sync-codex.sh:133-136) and the gates survive rewriting; do not commit the mirror.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-pilot/workflow.md:58-105,314-440,500-541,560-630`
- `plugins/flow-next/skills/flow-next-work/SKILL.md:160-250` + `phases.md:20-70,200-320,490-560`
- `plugins/flow-next/skills/flow-next-pilot/references/backlog-mode.md:250-340`
- `plugins/flow-next/docs/tracker-sync.md:110-130` — the shared 4-state contract (must keep matching)

**Optional:**
- `scripts/sync-codex.sh:130-160` — skill-dir copy mechanics

## Key context

Early proof point: fn-82.4 depends on this task. If the sentinel can't reliably force the Read or mirror parity breaks on new reference files, STOP and report — Class 2 gets re-evaluated before the eval-guarded class proceeds. Research constraints (binding): one-level-deep links; TOC >100 lines; verbatim moves (no paraphrase); fail open.

## Acceptance

- [ ] Default work run (bridge inactive) and default pilot tick (qa off) never load the new references (trace the gate branches); active paths emit the forcing sentinel and the behavior is equivalent
- [ ] Phase 5 sync-check + 4-state summary template inline and unchanged; R16/unlink prose still in SKILL.md
- [ ] QA_FRESH consumers (:334,:392 equivalents) untouched; Phase 5/6 qa routing untouched; backlog prose single-sourced, no stranded var reads
- [ ] New references have TOCs (if >100 lines) and are linked one level deep; gates fail open on probe error
- [ ] Local sync-codex run shows both new files mirrored + parity guards green (mirror not committed); canonical-only diff

## Done summary
Moved work's three tracker-touchpoint payloads + SKILL.md bridge overview into gated references/tracker-touchpoints.md and pilot's QA-freshness probe into gated references/qa-stage.md, each behind the spec's exact fail-open gate skeleton with a forcing GATE ACTIVE sentinel — default runs never load them (gate branches executed in all four scenarios). Also single-sourced pilot's backlog select/triage/ask prose to backlog-mode.md and work's delegation value-check to phases.md Phase 0, keeping Phase 5 sync-check + 4-state summary template, QA_FRESH consumers, Phase 5/6 qa routing, and R16/unlink prose inline; ~2.7k tokens cut from the always-loaded set; RP review SHIP (r2).
## Evidence
- Commits: cdedc470, 691c9a2d, 105d4add
- Tests: uvx --with pytest python3 -m pytest plugins/flow-next/tests/ -q  (1393 passed, 2 skipped — run WITH locally regenerated mirror), (cd $(mktemp -d) && bash .../scripts/smoke_test.sh)  (All tests passed), bash scripts/sync-codex.sh x2 (both new references auto-mirror; all parity guards green; mirror stashed, not committed — fn-82.5 regenerates), gate-block execution matrix in scratch repo: pipeline.qa gate default/on/probe-error/parse-error + sync-active gate inactive/active — sentinel fires only on active/error, QA_STAGE_ENABLED stays strict literal-on, targeted post-fix run: 134 passed; sole failure = expected canonical-without-mirror structural check (mirror regen deferred to fn-82.5 per R11), green after regen
- PRs: