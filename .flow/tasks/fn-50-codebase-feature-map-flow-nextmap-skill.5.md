---
satisfies: [R7]
---

## Description

Add one sub-criterion `DE7` to `/flow-next:prime`'s Pillar 5 (Dev Environment): *"Codebase feature map present? — `/flow-next:map` recommended for richer scope anchoring (optional)"*. Detection via `[[ -d .clawpatch ]]` + `flowctl repo-map list --count > 0`. Reporting is soft ❌ informational (mirrors the DC7 informational precedent); the criterion surfaces `/flow-next:map` in Top Recommendations. No auto-run.

**Size:** S
**Files:**
- `plugins/flow-next/skills/flow-next-prime/pillars.md` — add DE7 row to Pillar 5 table; mark informational
- `plugins/flow-next/skills/flow-next-prime/workflow.md` — wire DE7 into Top Recommendations surfacing logic (read-only — no remediation prompt)

**Depends on** fn-50.2 (uses `flowctl repo-map list --count`).

## Approach

**Pillar 5 prose alignment (already locked in spec):** Pillar 5 is **"Dev Environment"** (canonical name in current `pillars.md:96-114`). The original capture-time phrase "agent-readiness" referred to the Pillars 1-5 group label, not the Pillar 5 name. Use "Dev Environment" everywhere.

**Add to `pillars.md`** Pillar 5 criterion table (after DE6 at lines 96-114):

```
| DE7 | Codebase feature map present | `[[ -d .clawpatch ]]` + `flowctl repo-map list --count > 0` (informational — not scored) |
```

Mirror the **DC7 informational pattern** at `pillars.md:87` for the "not scored" annotation. DC7 is currently the canonical "informational, excluded from baseline scoring" precedent. DE7 follows the same shape.

**Criterion count update (locked in spec R7):** DE7 is **informational** (mirrors DC7). Pillar 5 stays at 6 scored / 7 total. Overall: **scored stays at 48** (DC7 + DE7 both informational, excluded from baseline); **total becomes 48 → 49**. No spec-correction needed — spec R7 already states this lock.

**Workflow wiring** at `plugins/flow-next/skills/flow-next-prime/workflow.md:175-180` (Top Recommendations section): when DE7 detection fires negative, surface the suggestion line:

> Consider: `/flow-next:map` — builds a semantic feature index for richer scope anchoring (optional).

DE7 must NOT appear in `workflow.md:190-313` (Phase 5 — remediation `AskUserQuestion` blocks). Per spec R7 "No auto-run."

**plugin.json count bump (out-of-scope for this task — owned by fn-50.6):** description string today claims "48 criteria"; DE7 informational means the scored count claim stays "48 criteria" (optionally "(+1 informational)" for clarity). Skill count "23 → 24" is the only mandatory string update in fn-50.6.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-prime/pillars.md:96-114` — Pillar 5 (Dev Environment) criterion table
- `plugins/flow-next/skills/flow-next-prime/pillars.md:87` — DC7 informational precedent
- `plugins/flow-next/skills/flow-next-prime/workflow.md:175-180` — Top Recommendations surfacing logic
- `plugins/flow-next/skills/flow-next-prime/workflow.md:190-313` — Phase 5 remediation prompts (DE7 MUST NOT appear here)
- Output from fn-50.2: `flowctl repo-map list --count` returns scalar

**Optional**:
- `plugins/flow-next/.claude-plugin/plugin.json` — description string count claim (informational; the bump is fn-50.6's job)

## Key context

- DC7 is the ONLY existing informational criterion in prime — fn-50.6 will need to bump prime documentation if the count interpretation changes.
- "Soft ❌" = informational ❌ surfaced as suggestion in Top Recommendations, NOT a Phase 5 remediation prompt. Matches DC7 exactly.
- DE7 detection cost is one `[[ -d ]]` + one `flowctl` call. Cheap.

## Acceptance

- [ ] R7: `pillars.md` Pillar 5 gains a `DE7` row with detection condition `[[ -d .clawpatch ]]` + `flowctl repo-map list --count > 0`
- [ ] R7: DE7 marked informational (mirrors DC7 pattern at `pillars.md:87`); not scored as a hard miss
- [ ] R7: Prose: *"Codebase feature map present? — `/flow-next:map` recommended for richer scope anchoring (optional)"*
- [ ] R7: `workflow.md` Top Recommendations surfaces `/flow-next:map` as suggestion when DE7 detection fires negative
- [ ] R7: DE7 does NOT appear in Phase 5 remediation prompts (no auto-run)
- [ ] R7: Pillar count remains 8; document the criterion-count interpretation (informational vs scored) in pillars.md prose
- [ ] Manual smoke: `/flow-next:prime` in this repo (where no `.clawpatch/` exists) reports DE7 as ❌ informational with the `/flow-next:map` suggestion
- [ ] Manual smoke: after `mkdir -p .clawpatch/features` (empty), DE7 still reports ❌ (count=0); after a real `clawpatch map` run, DE7 reports ✅

## Done summary

_To be filled by `/flow-next:work` on completion._

## Evidence

_To be filled by `/flow-next:work` on completion._
