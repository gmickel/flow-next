# Autoresearch changelog — spec-scout (plan-scout, output budget)

Each entry: experiment N, keep/discard, score, change, reasoning, result.
Lever: feature-preserving output budget (keep all real relationships; trim No-Relationship noise).
Run-trick: subagent + frozen inline open-specs corpus. Model held: claude-sonnet-4-6. 2 inputs.

## Experiment 0 — baseline
**Score:** 8/10 — E1 critical-coverage 2/2 (S1 os-1+os-3, S2 os-4+os-3), E2 precision 2/2, E3 grounded 2/2, E4 Lean 2/2, **E5 0/2** (enumerates "os-2, os-4, os-5, os-6: Unrelated scope").
**Key finding:** spec-scout output is ALREADY LEAN on a normal corpus (E4 passes ~93-100 tok). The only headroom is the **No-Relationship enumeration**, which is negligible at 6 specs but scales linearly with the spec count (a 50-spec repo → a 40+ id unrelated list). So this is a **small, scale-dependent** win, not a big output reduction. Still worth landing: No-Relationship ids are noise, not a feature.
**Side note:** S1 baseline mis-bucketed os-2 (rate-limiter wraps handlers.ts → the new route is affected) into No-Relationship — a detection nuance independent of the budget.
## Experiment 1 — KEEP
**Score:** 10/10 (baseline 8/10) — E1-E3 held 2/2 (all real relationships + grounding preserved), E4 Lean 2/2 (even leaner: S1 ~73 tok), **E5 0->2/2**.
**Change:** Output budget block — surface EVERY real relationship (never drop one), one line each with the concrete shared anchor, **No-Relationship is a COUNT not an enumeration**, omit empty relationship sections.
**Result:** No-Relationship "os-2, os-4, os-5, os-6: Unrelated" → "3 other open specs: no relationship." S1 also dropped the empty "Reverse Dependencies: None" heading. Coverage/precision/grounding unchanged. Honest framing: a SMALL win at typical scale (output was already lean) but **scale-robust** — the enumeration grew O(spec count), so a 50-spec repo now saves a ~47-id list. Feature-preserving (relationships are the load-bearing output; unrelated ids are noise). KEPT.
