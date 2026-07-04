# Changelog — audit suite (fn-84.5)

Model `sonnet`, `mode:autofix` emission. 3 stores: M1 (7 mixed), M2 (4 clean, over-flag guard), M3 (4 stress).
Ratchet: accuracy (E1-E3, incl. over-flag) never drops; keep iff accuracy ≥ baseline AND (accuracy↑ OR tokens↓ OR quality↑).

## The fable review caught a spoon-fed ceiling — and it was right
The FIRST baseline used frozen contexts that STATED conclusions in the taxonomy's own vocabulary ("problem
domain no longer exists", "both accurate, heavily overlapping") → a fake 4/4 (classification degenerated to
"don't contradict your own input"). The fn-84.5 fable review flagged it NEEDS_WORK. Fix: **every frozen context
rewritten as RAW investigation FACTS** (grep/git-log/symbol/code) with zero verdict adjectives — the run must
DERIVE each verdict. Origin of the standing lesson: **fable-review the eval DESIGN before the expensive runs.**

## Experiment 0 — CORRECTED facts-only baseline — 4/4 (EARNED this time)
- E1 6/6: M1-a Keep, M1-b Update (inferred the `_parse_frontmatter`→`_read_yaml_header` rename from grep facts),
  M1-c **mark-stale**, M1-f Replace, M1-g mark-stale, M3-b Update.
- **M1-c answer-key CORRECTION (mine to fix):** first keyed Delete; but the git-log fact says "superseded by
  flow-next-tui" → a successor exists → problem domain may persist → Delete (needs problem GONE) unsupported;
  correct verdict is **mark-stale**. audit classified it mark-stale in BOTH runs — correctly. The Delete key was
  the error (exactly the answer-key defect a pre-run design review catches).
- E2 over-flag 0 false positives on M2(4)+M3-a — audit read the raw fact (N+1 code present+unfixed) over M3-a's
  surface age. E3 delete-discipline: no over-deletion; ambiguous M1-c/M1-g → mark-stale. E4 quality 1/1:
  M1-d/e content-preserving Consolidate + M3-c Keep-both (both consolidate directions).
- **Genuinely earned** (facts not conclusions, correct keys, hard stress). **Fixture gap:** no clean-Delete case
  remains (M1-c → mark-stale) — add a no-successor Delete fixture next iteration.

## Experiment 1 — Delete-vs-mark-stale accuracy lever — DISCARD + REVERT
Chased the apparent "M1-c Delete over-conservatism" with a phases.md cue. Re-ran M1+M3: M1-c STILL mark-stale
— correctly (not a clean Delete). No accuracy change; no regression (M3-a stayed Keep — cue didn't over-flag).
REVERTED (prose byte-identical to baseline). A pre-run design review would have caught the mis-key and skipped this chase.

## Experiment 2 — trim — DISCARD-HOLD (inspection-backed)
rationale asides load-bearing; fn-N rule-carrying (fn-38); calibration proximity-load-bearing; fn-82.3 already
harvested −549 tok. Glossary + Phase 5/6 prose unexercised by fixtures (unverifiable, not load-bearing). No trim run.

## Net
EARNED ceiling (facts-only, correct keys, hard stress). No prose change (lever reverted). Durable: a
classification + over-flag + consolidate-restraint harness with facts-not-conclusions fixtures + the design-review-first process lesson.
