---
title: "Unit-rename substitution broke trigger thresholds (turns->rounds, fn-100)"
date: "2026-07-18"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-interview/references/doc-aware.md
tags: [interview, rounds, doc-aware, thresholds, spec-contract, impl-review, fn-100]
problem_type: build-error
symptoms: Mechanical <=6-turns -> <=6-rounds swap made fuzzy-term sharpening unreachable (full interview = 3-5 rounds)
root_cause: "Threshold sites renamed like throttle sites; threshold magnitude not re-derived for the new, coarser unit"
resolution_type: fix
related_to: [bug/build-errors/fn-44-review-cycle-lessons-2026-05-21, bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03]
---

## Problem
fn-100.1 renamed the interview's interaction unit from "turn" to "round" and R8 mandated a mechanical substitution at all six doc-aware.md "per interview turn" sites. Codex impl-review (r1, Major) caught that two of the six are TRIGGER thresholds, not throttles: "<=6 turns" (skip fuzzy-term sharpening in short conversations) became "<=6 rounds" - but a full rounds interview is only 3-5 rounds, so behavior (b) became effectively unreachable, contradicting R8's own "Intent preserved" clause.

## What Didn't Work
Applying the spec's literal wording ("all six sites per-round") uniformly. A threshold measured in the old unit does not survive a unit rename when the unit's typical magnitude changes (10-20 turns vs 3-5 rounds per interview).

## Solution
Split the six sites by role: four genuine throttle/cadence sites (one glossary question / one decision write / one strategy question / glossary re-read) became per-round; the two behavior-(b) trigger sites stayed observation-based ("<count> replies", "<=6 user replies") - doc-aware.md:63,78. Review r2 then required amending the governing contract (spec R8 + task acceptance) to match, so the stale contract could not invite restoring the regression. SHIP on r3.

## Prevention
- When a spec renames a unit of interaction/measure, audit each substitution site by ROLE: cadence/throttle sites rename cleanly; threshold/trigger sites need their magnitude re-derived in the new unit or an observation-based measure.
- A mechanical "replace X with Y at all N sites" acceptance criterion deserves a per-site semantic check during planning, not just at review.
- When a review-driven fix deviates from an acceptance criterion's letter to honor its stated intent, amend the spec/task contract in the same fix loop - implementation and contract must not disagree at done.
