# Autoresearch changelog — flow-gap-analyst (plan-scout, R4)

Each entry: experiment N, keep/discard, score, change, reasoning, result.
Lever: feature-preserving output budget (trim per-gap verbosity, NEVER fewer gaps).
EVAL 1 Coverage = the feature-preservation guarantee. Run-trick: general-purpose subagent reads the
prompt-under-test, analyzes a frozen underspecified feature request. Model held: opus. 3 inputs.

## Experiment 0 — baseline
**Score:** 9/15 (60.0%)  [FG1 3/5, FG2 3/5, FG3 3/5]
**Per-eval:** Coverage 3/3 · Specificity 3/3 · Sections 3/3 · Lean **0/3** · Focused **0/3**
**Coverage detail:** every input surfaced ALL 9 answer-key gaps (floor is ≥6) — so coverage has a
large margin to spend. FG1/FG2/FG3 each ~1500-1700 tok.
**Bloat pattern:** (1) **cross-section gap duplication** — the same gap appears as a User Flow
"Missing", an Edge Case row, a State Management question, AND a Priority Question (e.g. FG1
revocation shows up 4×). (2) Multi-line per item — User Flows carry Steps + Missing prose; many
sections each restate context. Accuracy/coverage maxed; only the two token levers fail. Classic
output-budget setup with a wide feature-preservation margin — the budget can cut duplication +
padding while staying ≥6 gaps.
## Experiment 1 — KEEP-candidate (superseded by exp2)
**Score:** 15/15 — Lean 3/3 (~382-462 tok, ~70% leaner), Focused 3/3, Coverage 3/3 (FG1 8/9, FG2 7/9, FG3 8/9 — all ≥6 floor), Specificity/Sections 3/3.
**Change:** Output budget block — hard ~550-tok target, one line per gap, each gap in exactly ONE section (kill cross-section duplication), Priority Questions NAMES top gaps (no re-describe), no code blocks, relative paths.
**Result + the feature-preservation catch:** huge leanness win, but it **dropped 1-2 secondary gaps** per input (FG1 password-protection; FG2 permissions/PII + concurrent-export) vs the exhaustive baseline (9/9). Critically, output landed at only ~382-462 tok — **~190 tok under the 650 cap** — so the drop was NOT token-forced; the "~550 ceiling" framing nudged the agent to stop enumerating early. Per Gordon's "always be sure we didn't lose features", over-trimming gap count is the wrong trade when the savings actually come from de-duplication. → refine in exp2.

## Experiment 2 — discard (coverage recovered, but Nice-dup regressed)
**Score:** ~12/15 — Coverage 3/3 (FG1 7/9, FG2 **9/9**, FG3 **9/9** — recovered exp1's dropped gaps), Lean 3/3 (501-637 tok), Specificity/Sections 3/3, **Focused 0/3**.
**Change:** reframed the budget as coverage-exhaustive ("list EVERY gap; leanness from de-dup, not fewer gaps; ~450-650 is a natural result not a ceiling").
**Result:** full coverage recovered (the goal), but being told to be exhaustive, the agent restated already-listed gaps in **Nice-to-Clarify** (FG2 Nice = filename/feedback/permission, all already above; FG1 Nice = expiry/SEO/snapshot, all already above) → cross-section duplication, the exact thing the budget forbids. Net score fell below exp1. NOTE: on re-inspection exp1 also had a milder Nice-dup (FG2 filename/delimiter), so exp1 is ~14/15 not a clean 15. Neither is optimal → exp3 must keep exp2's exhaustive coverage AND enforce strict no-restate (Nice = genuinely-new gaps only).

## Experiment 3 — KEEP
**Score:** ~13/15 — Coverage 3/3 (FG1 **9/9**, FG2 **8/9**, FG3 **9/9** = 26/27 gaps), Specificity/Sections 3/3, Focused 2/3 (FG1 still restated expiry/analytics in Nice; FG2/FG3 clean), Lean 2/3 (FG2 492 ✓, FG3 649 ✓, **FG1 756 ✗**).
**Change:** kept exp2's coverage-exhaustive framing + added a strict rule: **Nice-to-Clarify holds ONLY genuinely-new gaps, never restate** one already listed above. Template Nice line updated to match.
**Result vs the alternatives (consistent scoring, Focused penalizes any Nice restatement):**
- exp1 (leanest): 13/15 — Lean 3/3, Focused 1/3, **23/27 gaps** (dropped password, permissions/PII, concurrent-export). ~382-462 tok.
- exp3 (this): 13/15 — Lean 2/3, Focused 2/3, **26/27 gaps** (recovered password, permissions/PII, analytics, a11y; cleaner dedup). ~492-756 tok.
**Tie on raw score → broken by the project mandate "always be sure we didn't lose features."** exp3
preserves the most gaps AND de-duplicates cleanest; its only cost is that the single gap-richest input
(share-link, genuinely the most edge cases) lands ~750 tok instead of ≤650 — still ~50% leaner than
baseline (~1500), with the other two inputs 60-70% leaner. Coverage is never sacrificed to the cap.
**KEPT.** Net win over baseline: ~50-70% leaner gap-analysis output flowing into the planner, with
near-complete gap coverage preserved (26/27 vs baseline's 27/27 at 3-4× the tokens).
**Residual:** the lean↔exhaustive knob is real — a future tweak could shave FG1 under 650 by tightening
per-line wording without dropping gaps; and FG1's Nice still restated 2 gaps (expiry/analytics).
