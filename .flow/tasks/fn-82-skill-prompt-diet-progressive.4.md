---
satisfies: [R4, R8]
---

## Description

The eval-guarded pair, baseline-first ratchet per agent_docs/optimizing-skills.md: (a) make-pr — fold phases.md into workflow.md's inline Done-when blocks and stop force-loading it; (b) capture — dedupe far-from-consumer table copies across the always-loaded pair. Each change is kept ONLY if its eval suite holds the recorded baseline; regression → revert + log the discard row. Depends on fn-82.1.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-make-pr/{SKILL.md,workflow.md,phases.md}`, `plugins/flow-next/skills/flow-next-capture/{workflow.md,phases.md}`, `optimization/make-pr/results.tsv`, `optimization/capture/results.tsv`, `agent_docs/optimization-log.md`

## Approach

- **Procedure (both items, in order):** (1) read each suite's actual files — `optimization/make-pr/{README.md,evals.md,fixtures/,results.tsv}` and `optimization/capture/{README.md,evals.md,test-inputs.md,baseline/,results.tsv}` (make-pr has fixtures/, NOT test-inputs.md); (2) run the eval agent-driven on the CURRENT branch per optimizing-skills.md §"How to run a flow-next skill" (dispatch read-only subagents against the frozen inputs; prompt-under-test = live skill files); (3) record the baseline row in results.tsv; (4) apply the mutation; (5) re-run identically; (6) keep iff score ≥ baseline, else `git checkout` the mutation away and log the discard. Never skip the baseline (a ratchet without a recorded baseline proves nothing).
- **make-pr fold (FOLD, not gate — checklists are consumed every run):** first verify authority direction — diff each phases.md `**Done when:**` block against workflow.md's inline `### Done when` (:272,:352,:607,:1044,:1228,:1599,:1864 — relocate by content); fold any richer phases.md detail INTO the inline blocks (verbatim), then reduce phases.md to a thin stub/index — DELETION FORBIDDEN (links may target it) — remove it from SKILL.md:16's force-load list, and sweep skill/doc/test references to phases.md (grep) so nothing force-loads or misdescribes it. Expected saving ~6k/run.
- **capture dedupe (the skill that regressed before — proximity is load-bearing):** dedupe ONLY copies far from their consuming step. Known consuming sites: biz-routing table consumed at workflow.md §2.6 (:298,:305 region) — the phases.md:101-122 copy may be the far one IF workflow.md's copy sits beside §2.6; verify by content first. Forbidden-behaviors + source-tag taxonomy: same analysis. Hard adjacency acceptance: the SURVIVING copy of each deduped table must sit in workflow.md §2.6 beside the drafting step that consumes it — if the dedupe would leave the surviving copy anywhere else, revert/skip and log considered-and-skipped. When in doubt, don't dedupe.
- Both results (kept or discarded) get optimization-log.md rows (fn-82.5 consolidates; write the rows here while evidence is fresh).

## Investigation targets

**Required:**
- `agent_docs/optimizing-skills.md` — §"How to run", §"Accuracy guard", capture precedent
- `optimization/make-pr/` (README, evals.md, fixtures/, results.tsv) + `optimization/capture/` (README, evals.md, test-inputs.md, baseline/, results.tsv)
- `plugins/flow-next/skills/flow-next-make-pr/phases.md` (full) + workflow.md Done-when blocks
- `plugins/flow-next/skills/flow-next-capture/phases.md:90-210` + `workflow.md:270-360` (post-fn-81 content — relocate by content)

## Key context

optimization-log precedent rows: make-pr "body held 5/5" (the bar to hold); capture DRY-trim 15/15→14/15 REVERTED (the trap: relocating a routing table away from its consumer flattened Decision Context). The eval IS the no-feature-loss guarantee — trust it over intuition in both directions.

## Acceptance

- [ ] Baseline rows recorded BEFORE each mutation in results.tsv using the file's EXISTING schema (no new columns); timestamps + run context go in the optimization-log.md row / changelog notes
- [ ] make-pr: phases.md no longer force-loaded; body eval held at baseline (or fold reverted + discard logged)
- [ ] capture: each dedupe either passes the suite at baseline or is reverted/skipped with a logged reason
- [ ] optimization-log.md rows written for both outcomes
- [ ] Canonical-only diff; smoke green locally

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
