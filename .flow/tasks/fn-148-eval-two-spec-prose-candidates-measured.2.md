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
Blocked:
Parked 2026-07-30 at the user's request.

**Progress: screen is 20/20 drawn, 3/5 cells scored** (G1, F1, G2 - see
`runs/screen/scores/` in the study, raw scorer transcripts archived alongside).
E6 cost is scored deterministically for all 20 draws. All 5 fixtures are blinded
and their blind inputs generated.

**Why it stopped:** the F2 and F3 scorer agents were killed mid-run by a session
quota limit, not by anything in the study or the data.

**Resume:** `~/work/agent-evals/studies/spec-prose-2026-07/RESUME.md` (commit
`be49c6d`, pushed). It carries the two remaining units of work - score F2, score
F3 - plus the full scorer-prompt contract, including the symbol-existence
spot-check that surfaced the G2 fabrication.

**Decision rule deliberately NOT run.** `PREREGISTER.md` makes the screen a
candidate nomination only, and running the rule on 3 of 5 cells is exactly the
post-hoc move pre-registration exists to prevent.

**Interim read (not a verdict):**

- The primary endpoint E2 failed as an *instrument*. Keys are 55-94% unanimous
  per cell; G1 resolves to 1 discriminating item out of 14 DISC items. Direction
  is inconsistent across cells - MV best on G1 and worst on F1, A0 never last and
  tied for best on G2. No arm wins twice.
- The signal is in the two predeclared guards instead. E5's spot-check caught the
  most heavily provenance-marked arm (G2 MV) attaching `verified` to a symbol that
  does not exist. G1's MV drew a false conclusion from a real, accurately-quoted
  probe. F1's A0 is the only outright fabrication across three cells.
- A0's E5 failures are close to definitional (it was never asked to mark
  provenance) and are recorded as an instrument check, never as a quality result.
- Cost, n=5: M +23.5%, V +36.7%, MV +38.8%. All three sit at or past the ~34%
  that sank the previous study's candidate on at least some fixtures.

A null or `INCONCLUSIVE` remains the most likely honest outcome; both are
first-class reportable results under this study's methodology.
## Evidence
- Commits:
- Tests:
- PRs:
