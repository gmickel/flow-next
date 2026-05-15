---
satisfies: [R24, R25]
---

## Description

Extend `/flow-next:capture` to route explicit conversation signals across the nine business-context destinations. Source-tagged routing only (`[user]` / `[paraphrase]`). Sections without conversation signal stay absent — capture never auto-populates from nothing. End-of-flow suggestion footer fires when biz signals present but the biz layer is sparse, pointing to `/flow-next:interview --scope=business` as the next step.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` (routing instructions)
- `plugins/flow-next/skills/flow-next-capture/workflow.md` (Phase 2 section-by-section drafting; routing rules)
- `plugins/flow-next/skills/flow-next-capture/phases.md` (source-tag taxonomy update)

## Approach

Routing destinations per signal type (fn-44 R24):
| Signal | Destination |
|---|---|
| Target user / persona | Goal & Context |
| Problem framing / why-now | Goal & Context |
| Success metrics / definition of done | outcome-AC + `## Decision Context > ### Motivation` |
| MVP scope / "not doing X yet" | Boundaries |
| Business constraints (regulatory, deadlines, budget) | `Goal & Context` or `## Decision Context > ### Motivation` |
| What NOT to build | Boundaries |
| Prioritization rationale | `## Decision Context > ### Motivation` |
| Business risks | `Goal & Context` or `## Decision Context > ### Motivation` |
| UX expectations | Goal & Context |

Routing happens during Phase 2 source-tagged synthesis (`workflow.md:274-298`). Sections without conversation signal stay absent.

Sparse-layer heuristic for R25 suggestion: count of distinct SIGNAL CATEGORIES (per R24, nine total) with detected content is `>= 1` AND `< 3`. Zero categories → suggestion does NOT fire (preserves R22 — solo dev with no biz signals sees nothing). Three or more → suggestion does NOT fire (biz layer is reasonably filled). The threshold decision is delegated to `flowctl scope suggest --signal-categories-count <N>` (shipped by fn-44.1) — capture passes the count, flowctl returns `fire` / `no-fire` (`--json` exit codes also differ — 0 for fire, non-zero for no-fire — useful for `if "$FLOWCTL" scope suggest ...` shell checks). <!-- Updated by plan-sync: fn-44-symmetric-interview.2 confirmed scope suggest is the canonical threshold helper; capture skill must call it rather than re-implementing the `1 <= count < 3` math inline (skill-vs-flowctl architectural rule). --> When triggered, append the suggestion line to the Phase 4 read-back footer:

> "This conversation has business-requirements signals; consider `/flow-next:interview --scope=business <spec-id>` to deep-refine the business layer."

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-capture/workflow.md:274-298` — Phase 2 section-by-section drafting
- `plugins/flow-next/skills/flow-next-capture/phases.md:88-128` — source-tag taxonomy
- `plugins/flow-next/skills/flow-next-capture/workflow.md:77,106` — strategy-snapshot input flow (precedent)
- fn-44 spec R24, R25

**Optional:**
- `plugins/flow-next/skills/flow-next-capture/SKILL.md:140-143` — pipeline overview

## Acceptance

- [ ] Capture routes target-user / problem-framing / success-metric / MVP-scope / constraints / non-goals / prioritization / risks / UX signals to their respective sections
- [ ] Sections without conversation signal stay absent (no empty-section auto-populate)
- [ ] Suggestion footer fires when `1 <= count < 3` of the nine SIGNAL CATEGORIES (per R24) received content. Zero categories → no suggestion (R22 invariant). Three+ → no suggestion (biz layer adequate).
- [ ] Suggestion uses generic phrasing ("business-requirements signals; consider `/flow-next:interview --scope=business <spec-id>`")
- [ ] Capture asks no new questions; pre-existing read-back loop preserved
- [ ] Capture skill files (SKILL.md / workflow.md / phases.md) cross-link `plugins/flow-next/templates/spec.md` when naming section structure (per R17); no inline-duplicated section lists

## Done summary
Extended `/flow-next:capture` skill (SKILL.md / workflow.md §2.2 + §2.6 + §Manual-smoke + Phase 6 footer / phases.md source-tag taxonomy) to route the nine R24 biz-context SIGNAL CATEGORIES to canonical-template destinations using only `[user]` / `[paraphrase]` tags, with sections receiving no conversation signal staying absent. Phase 6 calls `flowctl scope suggest` (T1 plumbing, never re-implements the `1 <= N < 3` threshold inline) to fire/no-fire the R25 `/flow-next:interview --scope=business` suggestion footer. Cross-linked `plugins/flow-next/templates/spec.md` per R17 instead of re-enumerating canonical sections inline. Codex mirror regen via `sync-codex.sh`; SHIP verdict at `codex:gpt-5.5:high` after one NEEDS_WORK cycle (R17 enforcement beyond the R21 awk drift-guard).
## Evidence
- Commits: 3cbde773732663c8e580af3c8e80723cbf7f4c80, 0ae9d76e58080e3089486f02330c6ce18e21fdf3, 29a0a299e00c1134486a8e8d39e6a4fd3c9b2f24
- Tests: bash scripts/sync-codex.sh (R21 canonical-section duplication guard + all other validators pass), flowctl scope suggest --signal-categories-count {0,1,2,3} --json (verified fire/no-fire decision matches spec — N=0 no-fire exit 0; N=1,2 fire exit 0; N=3 no-fire exit 0; plain mode: fire→exit 0, no-fire→exit 1), flowctl codex impl-review fn-44-symmetric-interview.5 --base de8f1ec --spec codex:gpt-5.5:high → SHIP after 1 NEEDS_WORK fix cycle
- PRs: