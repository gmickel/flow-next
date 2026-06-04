# Autoresearch changelog — repo-scout

Each entry: experiment N, keep/discard, score, change, reasoning, result.

## Experiment 0 — baseline
**Score:** 10/12 (83.3%)  [T1 4/4, T2 3/4, T3 3/4]
**Per-eval:** Grounded 3/3 · Tagged 3/3 · Lean **1/3** · Focused 3/3
**Failure pattern:** output too long — T2 ~1130 tok, T3 ~825 tok (cap 700). Causes: absolute `/Users/...` paths (T1,T2), bold sub-headers + grouping prose (T2), Python "pattern" code blocks (T3), 6+ items per section.
**Side finding (not in eval set):** T1 skipped Step 0 and omitted `features_anchored` though `.clawpatch/` has 9 features — a coverage/consistency miss a future eval should catch.

## Experiment 1 — KEEP
**Score:** 12/12 (100%)  [T1 4/4, T2 4/4, T3 4/4]
**Per-eval:** Grounded 3/3 · Tagged 3/3 · Lean **3/3** (was 1/3) · Focused 3/3
**Change:** Added a hard "Output budget" block high in the Output Format section: repo-relative paths only (never absolute `/Users/...`), top 3–5 items per section, one line per finding (no bold sub-headers / grouping prose), no code blocks (signature named inline), omit empty sections.
**Reasoning:** Baseline's only failing eval was Lean; the bloat came from absolute paths, code blocks, sub-headers, and uncapped item counts — all addressable by one budget rule placed where the model reads it before formatting.
**Result:** Every output dropped ~40–50% (baseline T2 ~1130 tok → ~600; T3 ~825 → ~400; T1 stayed lean). Grounding + tags held; coverage of the key files (set_config, get_default_tracker_config, json_output, the make-pr touchpoint) preserved — the cap trimmed redundancy, not signal. Focused improved (T3 dropped its Python pattern blocks). Bonus: T1 ran Step 0 and correctly emitted features_anchored this time.
**Residual (for a future experiment):** T2 still used bold sub-headers and landed ~600 tok (budget target was 500) — a follow-up mutation could harden "one line per finding / no sub-headers" or tighten the Lean eval cap to 500. Also missing: a COVERAGE eval to guard against the cap trimming real signal on harder inputs.
