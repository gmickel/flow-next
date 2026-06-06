# Binary evals (5) — max per run = 5; max_score = 5 × 3 inputs = 15

EVAL 1 (Coverage) is THE feature-preservation guarantee. A token-budget mutation is kept only if
Coverage holds (never trades gaps for tokens). 3 of 5 are accuracy/coverage evals (R3).

EVAL 1: Coverage  [FEATURE PRESERVATION — the load-bearing eval]
Question: Does the output surface ≥6 of the input's answer-key critical gaps (named explicitly or as
an unambiguous equivalent question)?
Pass: ≥6 of the per-input answer-key gaps are surfaced anywhere in the output.
Fail: <6 answer-key gaps surfaced (the mutation lost coverage = lost a feature).

EVAL 2: Specificity / grounded  [ACCURACY]
Question: Are the surfaced gaps SPECIFIC and actionable (per the prompt's own rule — "what about
errors?" is too vague), each tied to a concrete scenario/decision, not generic filler?
Pass: every Priority Question + Edge Case is concrete (a reviewer could act on it). No vague filler.
Fail: ≥2 vague/generic gaps ("handle errors", "consider edge cases") padding the output.

EVAL 3: Sections present  [ACCURACY / FORMAT]
Question: Are the applicable required sections present — at minimum User Flows, Edge Cases, Error
Handling Gaps, and Priority Questions (Design Gaps omitted is fine; no DESIGN.md)?
Pass: the four core sections render with content.
Fail: a core section missing or empty when the feature clearly has content for it.

EVAL 4: Lean  [TOKEN LEVER]
Question: Is the total output ≤ 650 tokens (~490 words)?
Pass: word count × 4/3 ≤ 650.
Fail: over 650 tokens.

EVAL 5: Focused (one line per gap, no bloat)
Question: Does the output obey lean discipline — one line per gap/question (no multi-line prose
padding per item), no fenced code blocks, no restating the same gap across multiple sections?
Pass: one line per finding; no code blocks; no cross-section gap duplication.
Fail: multi-line padding per gap, a code block, or the same gap repeated across sections.
