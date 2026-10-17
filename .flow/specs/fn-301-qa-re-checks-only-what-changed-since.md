# QA re-checks only what changed since its last pass

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 0% [user], 50% [paraphrase], 50% [inferred] -->

A QA verdict is fresh only at the exact code head it ran on. When anything changes the head afterwards (a fix for a QA finding, a small review fix, a rebase before the pull request), the next QA run derives and drives every scenario again, including the ones that passed and whose surface nothing touched. A live pass costs minutes per scenario, so one small fix after QA can cost a full live run. [paraphrase]

QA already refuses to re-drive criteria that work proved with a specific, re-runnable test. The same reasoning applies one level up: a scenario a previous QA pass proved live, on a surface nothing has touched since, does not need driving again. [paraphrase]

Target user: anyone running QA attended or as the `pipeline.qa` stage of `flow --auto`, who fixes something after a QA pass. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

- **Prior pass as input.** When the spec has a QA receipt from an earlier head on the same branch, QA reads it and the tree diff from that head to the current one (a tree diff, so a rebase's base changes count too). [paraphrase]
- **What re-runs.** Every scenario that failed or was blocked last time; every scenario whose surface the diff touches, where surface includes the code the scenario drives through and shared code it depends on (styles, state stores, routing, auth); scenarios for criteria the diff newly adds or changes; and one load-bearing scenario as a smoke run of the whole app. [paraphrase]
- **What carries.** A scenario that passed on the prior pass, on a surface the diff does not touch, carries its result, cited with the prior receipt's head and evidence. It is never re-labelled as captured at the new head. [paraphrase]
- **When to run in full.** No prior receipt, a prior receipt without per-scenario outcomes, a diff touching shared code broadly, a changed acceptance contract, or any doubt about what a surface depends on: QA runs in full as today. [paraphrase]
- **The new receipt.** It is written at the current head as today, and its coverage shows which scenarios ran at this head and which were carried from which head. SHIP still needs live evidence at this head for everything that re-ran; carried results count only as carried. [paraphrase]

## Examples
<!-- scope: both -->

**Fix after a finding.** QA on a checkout spec ran 9 scenarios at `a1b2c3`: 8 passed, "apply an expired coupon" failed (P1). The fix touches only `coupon/validate.ts` and its test. The next QA run re-drives the coupon scenario and its error variant, plus the full purchase path as the smoke run, and carries the 6 untouched passes (cart, address, payment, receipt email, guest checkout, saved cards) from `a1b2c3`. Three scenarios driven instead of nine. [inferred]

**Shared code touched.** The fix changes `ui/Button.tsx`, which every page uses: the diff touches shared code broadly, so QA runs in full. [inferred]

**Rebase before the PR.** The branch is rebased onto a base that changed only `docs/`: the tree diff touches no scenario surface, so QA re-drives only the smoke scenario and carries the rest. [inferred]

A coverage excerpt as it might read (shape illustrative):

```text
R3 apply coupon        live @ d4e5f6  PASS (screenshot qa/r3-coupon.png)
R3 expired coupon      live @ d4e5f6  PASS (screenshot qa/r3-expired.png)
R1 add to cart         carried @ a1b2c3  PASS (screenshot qa/r1-cart.png)
smoke: full purchase   live @ d4e5f6  PASS (video qa/smoke.webm)
```

[inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- A prior receipt from another branch or another spec is never used. [inferred]
- A smoke scenario that fails makes the run continue in full. [inferred]
- Carried results never satisfy an R-ID whose criterion text changed since the prior pass. [paraphrase]
- Freshness for `flow --auto` is unchanged: the new receipt is fresh at the new head. [paraphrase]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** With a prior QA receipt from an earlier head of the same spec and branch, QA re-runs failed and blocked scenarios, scenarios whose surface the tree diff touches (including shared dependencies), scenarios for new or changed criteria, and one smoke scenario, and carries the rest. Errors: no prior receipt or no per-scenario outcomes → full run; prior receipt from another branch or spec → ignored. [paraphrase]
- **R2:** QA runs in full when the diff touches shared code broadly, the acceptance contract changed, or the dependency of a surface is uncertain. Errors: a failing smoke scenario → continue in full. [paraphrase]
- **R3:** The new receipt at the current head shows which scenarios ran live at this head and which were carried, from which head, with their evidence; carried results are never labelled as captured at the new head. No error surface. [paraphrase]
- **R4:** SHIP rests on live evidence at the current head for every re-run scenario and on cited carried evidence for the rest; a changed criterion is never satisfied by a carried result. No error surface. [paraphrase]
- **R5:** On a live-app fixture with a small fix planted after a QA pass, the focused re-check takes less time than a full re-run and misses no regression the full run would catch. No error surface beyond the study's verdict. [inferred]

## Boundaries
<!-- scope: business -->

- Review is not scoped this way; review after fixes keeps its existing rules. [paraphrase]
- No change to how QA derives scenarios on a first pass, or to QA's evidence rules. [paraphrase]
- No new flowctl verb or receipt schema change beyond the coverage marking carried results. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

A full live run after a one-file fix is the largest avoidable cost in the QA stage; carrying untouched passes with their original evidence keeps every claim honest while driving only what could have changed. [paraphrase] Review is deliberately left out: scoping review to a delta was studied and parked after it lost recall, and nothing here changes that. [paraphrase]

Delivery order: 6 of 6 in this set; independent. Route: direct. [paraphrase]

## Strategy Alignment

Serves the **Autonomous mode** track: the opt-in QA stage costs less per fix while still augmenting, never replacing, CI and manual QA. Follows the **Agent first** design principle: the scoping is the agent's judgment, recorded in the coverage it already writes.

## Strategy Conflicts

None found.
