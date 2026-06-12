---
satisfies: [R2, R3, R6, R7]
---

## Description
THE core deliverable: the progressively disclosed reference file that lets any host-agent session generate house-style, self-contained HTML artifacts — plus its Codex-mirror wiring. The executable early proof runs in fn-62.3; this task ships the file "ready for proof".

**Size:** M
**Files:** plugins/flow-next/references/html-artifacts.md (new), scripts/sync-codex.sh (one sibling cp block)

## Approach
Structure per practice-scout (rules → worked example → checklist, NOT a design essay):
1. **Hard rules / non-goals:** self-contained single file — inline ALL CSS/JS, NO external requests of any kind (no CDN, no Google Fonts, no Tailwind; agents reach for CDNs by habit — be emphatic, include a self-check grep); render lens contract (markdown is the record; artifact regenerable, never parsed back); fixed output paths (`.flow/artifacts/<spec-id>/{spec,pr}.html`); idempotent spec-md link-line replacement (marker-based, never duplicated); staleness stamp in footer (spec updated_at + git commit at render); localStorage only try-wrapped progressive enhancement; print CSS (A4, light theme) mandatory.
2. **Positive design contract (anti-slop):** concrete house style as copy-pasteable CSS-var blocks — warm-black instrument-panel palette, monospace-led stack (Berkeley Mono/JetBrains/SF Mono/ui-monospace) + serif accent (Iowan Old Style/Palatino), hairline rules, uppercase micro-labels, amber/green/red/cyan semantic accents. Forbidden list verbatim: centered-everything, purple gradients, uniform rounded corners, Inter (cite anthropics web-artifacts-builder). Reverse-engineer from the validated smoke artifacts in ~/Documents/flow-next-artifact-smoke/ (fn-52 spec, PR #171, fn-62 pre-plan).
3. **Per-lens guidance:** spec lens (state-dependent: spec-only sections pre-plan; + task DAG + R-ID coverage matrix post-plan; source-tag provenance chips); PR lens (diff-derived dials, churn-by-review-intent groups, R-ID→evidence table, where-to-look checklist, risk register; R-ID mismatch rows flagged visibly).
4. **DAG discipline (top research risk):** layered CSS-grid/flex columns by dependency depth; edges via small inlined deterministic JS reading DOM positions at load — NEVER hand-typed SVG coordinates; >~20 nodes → lane/group collapse.
5. **Lavish block:** detect (`command -v lavish-axi`), interactive-only open + background poll, stable-path rule, conversational-regen instructions ("regenerate the artifact for <spec-id>"), autonomous = generate-only.
6. **Pre-publish checklist:** zero external URLs in src/href (assets), opens from file://, prints clean, staleness stamp present, links resolve, exactly one link line in the source spec md.
- Keep the file TOOL-NAME-AGNOSTIC (no AskUserQuestion/Task mentions) so no sync rewrite pass applies (avoids the R2 ask-block injection bug class — memories: r2-ask-block-must-never-anchor / codex-mirror-audit-must-verify-r2-block).
- sync-codex.sh: add a sibling `cp -R` for `plugins/flow-next/references/` next to the templates block (:141-145); verify the mirror copy is byte-identical (no rewrites should touch it).

## Investigation targets
**Required:**
- ~/Documents/flow-next-artifact-smoke/*.html — the three validated artifacts (house style source)
- scripts/sync-codex.sh:120-180 — copy loops + templates precedent
- plugins/flow-next/skills/flow-next-qa/SKILL.md:80-95 — cross-skill repo-relative reference pattern
**Optional:**
- .flow/memory/bug/build-errors/ — sync-codex pitfall entries

## Acceptance
- [ ] Reference file exists at plugins/flow-next/references/html-artifacts.md, structured rules → example → checklist, < ~400 lines
- [ ] Design contract is positive + concrete (CSS-var palette, named font stacks) AND carries the verbatim forbidden list
- [ ] DAG guidance mandates layered layout + DOM-measured edges; bans hand-typed coordinates
- [ ] Lavish section covers detect/open/poll/stable-path/conversational-regen/autonomous-never-polls
- [ ] Link-idempotency + staleness-stamp + fixed-path rules all present
- [ ] File contains zero platform tool names (grep AskUserQuestion|spawn_agent|Task: empty)
- [ ] sync-codex.sh copies it; mirror file byte-identical to canonical
- [ ] READY FOR PROOF: pre-publish checklist is complete and self-checkable; the executable proof (fresh session reproduces house style) runs and gates in fn-62.3

## Done summary
Shipped the shared HTML-artifacts disclosure reference at plugins/flow-next/references/html-artifacts.md (320 lines, rules -> design contract -> per-lens guidance -> DAG discipline -> Lavish -> pre-publish checklist; house style reverse-engineered from the three validated smoke artifacts; tool-name-agnostic) plus Codex mirror wiring: sync-codex.sh sibling cp -R for references/ (byte-identical mirror) and install-codex.sh copy to ~/.codex/references/. RP impl-review: SHIP after one fix round (grep portability, print-CSS A4 default, sync-codex.md docs).
## Evidence
- Commits: e4a426360fbdb6d97c95f16f066cd20f8ffc2a24, 5ba324d6ba4bcbb93396e0521037eb20431f4dc1
- Tests: python3 plugins/flow-next/tests/test_*.py (full sweep, all pass), ./scripts/sync-codex.sh (all validation guards green, idempotent re-run), cmp plugins/flow-next/references/html-artifacts.md plugins/flow-next/codex/references/html-artifacts.md (byte-identical), grep -E 'AskUserQuestion|spawn_agent|Task' on the reference file (empty), bash -n scripts/sync-codex.sh scripts/install-codex.sh, self-check grep probed against spaced fetch() input (catches it)
- PRs: