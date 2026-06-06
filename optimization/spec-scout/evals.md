# Binary evals (5) — max per run = 5; max_score = 5 × 2 inputs = 10

EVAL 1: Relationship coverage  [FEATURE PRESERVATION]
Question: Does the output surface every REAL relationship in the input's answer key (the required
Dependencies / Reverse-deps / Overlaps), correctly categorized?
Pass: all must-surface relationships present in the right bucket. Fail: a required relationship dropped or mis-bucketed.

EVAL 2: Precision (no fabricated relationships)  [ACCURACY]
Question: Does the output avoid claiming relationships that don't exist (no dep/overlap on a
genuinely-unrelated spec — os-5/os-6 for both inputs)?
Pass: no fabricated relationship on an unrelated spec. Fail: invents a dep/overlap that isn't real.

EVAL 3: Grounded reason  [ACCURACY]
Question: Does each surfaced relationship name a concrete shared anchor (a file/API/event), not a
vague "related scope"?
Pass: every relationship cites a concrete shared file/API/event. Fail: ≥1 vague/unjustified relationship.

EVAL 4: Lean  [TOKEN LEVER]
Question: Is the output ≤ 250 tokens (~190 words)?
Pass: word count × 4/3 ≤ 250. Fail: over 250 tokens.

EVAL 5: No-Relationship noise trimmed  [the budget target]
Question: Does the output AVOID enumerating every unrelated spec — i.e. No-Relationship is a count
or omitted, not a full id list?
Pass: unrelated specs are summarized (count) or omitted, not enumerated one-by-one.
Fail: lists each unrelated spec id individually (the uncapped-noise pattern).
