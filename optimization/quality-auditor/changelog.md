# Autoresearch changelog — quality-auditor (uncapped free-form agent, output budget)

Each entry: experiment N, keep/discard, score, change, reasoning, result.
Lever: feature-preserving output budget (trim per-finding verbosity, NEVER drop a finding / weaken
severity). Frozen input: slop-testbed slop+clean diffs. Model held: opus. The answer key is the
no-feature-loss guard.

## Experiment 0 — baseline
**Score:** 4/5 — E1 ✓ (Major bug #6 = Critical/Conf 100), E2 ✓ (reference finding set: #2 over-abstraction + #4 wrapper + keyOf as Consider/100/75, legacy-mode test as Should-Fix, #7 tautological-test + under-tested via Test Budget/Test Gaps), E3 ✓ (every finding tiered + valid anchor), E5 ✓ (clean review = Low/✅ Ship, no fabricated Critical/Should-Fix; one honest Conf-25 Consider), **E4 ✗** (slop review ~950 tok).
**Note:** baseline MISSED slop #1 (isValidEmailAddress duplicates src/email.ts validateEmail) — it praised the regex instead (email.ts not in the diff). Out of scope for the budget loop; #1 is a baseline detection gap, not a token-lever issue.
**Bloat pattern:** multi-line Risk:/Fix: per finding, long Test Gaps + Test Budget + Security Notes + What's Good paragraphs. Accuracy/coverage maxed; only the token lever fails. Output-budget setup.
## Experiment 1 — KEEP
**Score:** 5/5 (baseline 4/5) — fixed the only failing eval (Lean) while holding all feature-preservation evals.
**Change:** output-budget block — under ~500 tok, **one line per finding** (`**file:line** (Conf N): issue — fix.`; Critical may add ONE Risk line), no code blocks, relative paths, terse trailing sections (≤2 bullets each), keep the Suppressed line, and explicitly **never drop a finding or weaken severity/confidence** (every finding keeps its tier + one anchor).
**Result:** slop review ~950 → ~338 tok (**~63% leaner**). Feature preservation held: #6 fake-success bug still **Critical/Conf 100**; structural slop #2 (over-abstraction) + #4 (wrapper) at Consider/75; legacy-mode path + tautological test at Should-Fix/100; severity tiers + confidence anchors all intact. Clean-feature review stayed quiet (Low / ✅ Ship, no fabricated Critical/Should-Fix). KEPT.
**Residuals (run-variance, not budget-induced):** the budgeted slop run (a) elevated `registration.ts:152` read/write-path inconsistency to Critical (baseline didn't list it) — a severity judgment call on real slop, not a fabrication; (b) folded the `keyOf` vestigial-method finding into the broader #2 over-abstraction finding rather than listing it separately (reasonable consolidation). Neither is a coverage loss.
