# Autoresearch changelog — capture (accuracy-critical, R5)

Each entry: experiment N, keep/discard, score, change, reasoning, result.
Lever: accuracy-first, token 2nd. Run-trick: mode:autofix (no --yes) via general-purpose subagent.
Inputs: C1 clean-technical · C2 biz-signal-rich · C3 override-collision. Model held: opus.
All 5 evals are accuracy evals — a trim is kept ONLY if it holds every one (the ratchet IS the
accuracy guarantee, R3).

## Experiment 0 — baseline
**Score:** 15/15 (100%)  [C1 5/5, C2 5/5, C3 5/5]
**Per-eval:** Fidelity 3/3 · Source-tagged 3/3 · Read-back 3/3 · Override-guard 3/3 · Sections/forbidden 3/3
**C1 (clean technical):** 6 testable ACs, all [user]; evidence block + tally (`[user] 13 · [paraphrase] 6 · [inferred] 0`) + [inferred] breakdown all present; Decision Context FLAT (BIZ=0); no invented tech-stack. Clean.
**C2 (biz-rich):** routed categories 1/2/3/4/6, BIZ_SIGNAL_CATEGORIES=5; Decision Context SUBSTRUCTURED with `### Motivation` (cat 3 present); biz lines only [user]/[paraphrase], zero [inferred] in biz sections; tally present. (Cosmetic: one run wrote a stray `<!-- FLAT -->` comment above a correctly-SUBSTRUCTURED section — labeling blemish, structure correct.)
**C3 (override collision):** Phase 0.2 found 3+ strong matches vs existing `fn-91-request-dedup-cache`; autofix + no --rewrite → hard-error exit 2 with the "cannot resolve duplicates / re-run with --rewrite" message. Never reached Phase 5; **explicitly preserved the user's hand-edited boundary** (no distributed cache). The R5 no-silent-overwrite guard works exactly as specified.
**Conclusion:** capture is accuracy-correct as written. The eval suite is now a permanent regression harness for the R5 spec-override guarantee. Next: attempt a conservative DRY token-trim that MUST hold 15/15 (revert otherwise).

## Experiment 1 — DISCARD (reverted)
**Score:** 14/15 (93.3%)  [C1 5/5, C2 **4/5**, C3 5/5] — below baseline 15/15 → revert.
**Change (one hypothesis = DRY trim):** removed two tables from `workflow.md` that are fully
duplicated in `phases.md` (the skill's mandated "taxonomy lookup" companion), replacing each with a
cross-link: §2.1 source-tag taxonomy table, §2.6 nine-category biz-routing table. ~284 tokens off
workflow.md, zero *intended* behavior change (phases.md is always loaded).
**Result:** C1 held (clean, all ACs [user], FLAT correct). C3 held (correctly refused, exit 2,
preserved the user hand-edit — override guard intact). **C2 regressed:** the success-metric signal
("the whole point is cutting support load — ~15% of ticket volume" = R24 category 3) was
**under-routed** — the trimmed run sent it to `Goal & Context` framing only and chose Decision
Context **FLAT**, explicitly (wrongly) asserting "none of categories 3,5,7,8 carried signal."
Baseline (untrimmed) routed category 3 to `### Motivation` + an outcome-AC → Decision Context
**SUBSTRUCTURED**, which is the spec-correct shape (§2.6: category 3 destination = outcome-AC +
`### Motivation`). E5 (Decision Context shape) failed for C2.
**Why it regressed:** the inline §2.6 routing table sits right beside the §2.2 drafting step. Moving
it one indirection away (into phases.md) made the agent more likely to skim the category→destination
mapping and mis-handle the success-metric → Motivation routing. The "duplication" is not redundancy
— it is **accuracy-load-bearing proximity**. Exactly the failure mode R5 warns about ("a trim must
not make the skill skim an important section").
**Decision:** REVERT. The ratchet did its job — a token-trim that *looked* self-evidently safe was
caught lowering accuracy by one real eval, on the precise behavior the trimmed table governs. This
validates R3 (real accuracy evals make the ratchet meaningful).

## Conclusion (this pass)
capture is **already accuracy-correct and well-tuned**; no safe token-trim was found in one
experiment (the obvious DRY candidate regressed biz-routing). The durable R5 deliverables stand:
1. A permanent accuracy-guard eval suite (5 accuracy evals incl. the override guard) for capture.
2. Verified baseline 15/15 — the no-silent-overwrite-of-a-user-edited-spec guarantee (C3) holds.
3. A documented instance of the ratchet catching a subtle regression — evidence the methodology's
   accuracy guarantee is real, not theoretical.
A future experiment could try a *non-routing* trim (e.g. compressing the §5.0 strategy-override
heredoc, which is verbose and NOT exercised by these inputs) — but routing/taxonomy tables in
workflow.md should be treated as load-bearing and left in place.

## Experiment 2 — re-baseline (fn-82.4, 2026-07-02)
**Score:** 15/15  [C1 5/5, C2 5/5, C3 5/5]. Fresh baseline on the fn-82 branch (post fn-81
single-emission reshape) before the far-copy dedupe — the exp-0/1 rows predate that reshape.
C1: all ACs [user]/[paraphrase], tally + [inferred] breakdown, Decision Context FLAT. C2: cat-3
success-metric routed to outcome-AC R7 + `### Motivation`, SUBSTRUCTURED, zero [inferred] in biz
lines. C3: refused (exit 2), named fn-91, no draft — override guard intact.

## Experiment 3 — KEEP (fn-82.4 far-copy dedupe, inverse of exp 1)
**Score:** 15/15 (held baseline)  [C1 5/5, C2 5/5, C3 5/5]
**Change (one hypothesis = dedupe the FAR copy, survivor at the consumer):** exp 1 (discarded)
removed the workflow.md §2.6 copy and regressed C2. This experiment does the inverse: the FULL
nine-category routing table (incl. the trigger-phrasing column) + the 2 rules that existed only
in phases.md moved verbatim INTO workflow.md §2.6 — right beside the §2.2 drafting step that
consumes it — and phases.md §Biz-context signal routing became a pointer (−3.9KB). Net
always-loaded saving ~2.5KB (~630 tok)/run. Source-tag taxonomy + forbidden-behaviors recap were
analyzed and SKIPPED (complementary copies / imperative-rules-at-action-site — see
optimization-log.md row).
**Result:** C2's cat-3 routing held (outcome-AC R6 + `### Motivation`, SUBSTRUCTURED) — the exact
behavior exp 1 broke. C3 still refuses (exit 2, names fn-91, preserves the hand-edit). C1 clean
(Decision Context stayed non-substructured for the zero-biz input; this run omitted the section
entirely per the empty-by-default rule where baseline wrote a FLAT body — R22-consistent either
way, no scaffolding leaked). KEEP.
