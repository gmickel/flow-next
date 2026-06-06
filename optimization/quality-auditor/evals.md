# Binary evals (5) — max = 5. Evaluated across the slop review (E1-E4) + clean review (E5).

4 of 5 are feature-preservation / accuracy evals (R3). A token-budget mutation is kept only if it
holds them — the slop-testbed answer key is the no-feature-loss guarantee.

EVAL 1: Major bug caught  [FEATURE PRESERVATION — critical]
Question: Does the slop review flag the fake-success error-swallow (#6: `catch { ... return {success:true} }`
+ `as any`) as a high-severity finding (Critical/Should-Fix, confidence ≥75)?
Pass: #6 surfaced as a high-severity, high-confidence finding.
Fail: #6 missed or downgraded to a minor/Consider note.

EVAL 2: Structural-slop coverage held  [FEATURE PRESERVATION]
Question: Does the budgeted review catch the same substantive findings the BASELINE caught — i.e.
no real finding dropped to save tokens? (Baseline finding set is the reference; budgeted ⊇ it for
all findings ≥ Should-Fix / confidence ≥75. The structural-slop items in scope: #1 duplicated
email-validation, #2 speculative repo/provider abstraction, #4 pass-through wrapper, #5 dead
legacy path, #7 tautological test.)
Pass: budgeted surfaces every ≥Should-Fix / ≥75-confidence finding baseline surfaced.
Fail: budgeted drops a finding baseline flagged at Should-Fix+ / ≥75.

EVAL 3: Severity + confidence intact  [ACCURACY]
Question: Does every finding carry a severity tier AND exactly one valid confidence anchor
(0/25/50/75/100, no interpolated values), with no severity weakened vs baseline?
Pass: all findings tiered + anchored; no weakening.
Fail: a finding loses its severity/confidence, an interpolated anchor appears, or a P0/Should-Fix is
softened to Consider.

EVAL 4: Lean  [TOKEN LEVER]
Question: Is the slop review output ≤ 550 tokens (~415 words)?
Pass: word count × 4/3 ≤ 550.
Fail: over 550 tokens.

EVAL 5: No false positives on clean  [FEATURE PRESERVATION / ACCURACY]
Question: On clean-feature.diff (no planted issues), does the review stay quiet — `✅ Ship`, no
fabricated Critical/Should-Fix findings (real boundary validation, a focused function, normal tests
are NON-goals and must not be flagged as slop)?
Pass: clean review = Ship, zero fabricated Critical/Should-Fix.
Fail: invents a Critical/Should-Fix finding on clean code (false-positive machine).
