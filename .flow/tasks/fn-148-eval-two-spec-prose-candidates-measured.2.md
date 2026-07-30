---
satisfies: [R5, R9]
---
# fn-148-eval-two-spec-prose-candidates-measured.2 Screen: one draw per cell, blind consolidated scoring, cost axes

## Description
Run the screen: one draw per cell (4 arms x all fixtures), blind-label, score with ONE consolidated standard, measure both cost axes. Identify the candidate (if any) for replication. All in ~/work/agent-evals.

**Size:** M

### Approach

- Blind labels via `lib/evalkit.py`; arm map outside the blind dir, never given to a scorer or subject.
- One scoring standard applied item-by-item ACROSS arms (never one scorer per artifact - the ranking inverted last time).
- Cost per arm: LF-normalized spec chars AND downstream-consumer output size.
- Log every draw and discard in changelog.md, including hostile ones. Report the discriminating-question subset separately from raw totals.
- Screen output is a candidate nomination, not a keep: no conclusion language beyond "candidate for replication" is permitted at this stage.

### Key context

Last study's screen showed +2/+2/+1 that replication collapsed to +0.33/+2.67/-0.33. Treat every screen number as provisional by construction.

## Acceptance
- [ ] One draw per cell authored and blind-labelled; map stored outside blind dir
- [ ] Consolidated single-standard scoring across all arms; per-item thresholds stated before verdicts
- [ ] Both cost axes recorded per arm
- [ ] Discriminating vs no-signal items reported separately
- [ ] changelog.md carries every draw and every discard; screen framed as candidate-nomination only


## Done summary
Closed by human decision on 2026-07-30 before completion. The screen produced 20/20 draws and deterministic cost scores, but only 3/5 cells were blind-scored; F2 and F3 remain unscored. The pre-registered decision rule was not run, so this task makes no candidate nomination or study verdict.
## Evidence
- Commits: agent-evals:c7b6dc2
- Tests:
- PRs: