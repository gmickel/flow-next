# Autoresearch changelog — docs-scout (output budget: pointer-not-paste)

Each entry: experiment N, keep/discard, score, change, reasoning, result.
Lever: feature-preserving output budget. Web-backed; eval = format budget + must-keep API/gotcha
survival (answer key). Model held: opus. 2 inputs (Express rate-limit / Zod validation).

## Experiment 0 — baseline
**Score:** 6/10 — E1 2/2 (docs+APIs), E2 2/2 (gotchas), E5 2/2 (real URLs), **E3 0/2** (code blocks + multi-line excerpts + exhaustive option lists), **E4 0/2** (D1 ~1200 tok, D2 ~870 tok).
**Bloat:** "Don't just link - extract the relevant parts" drives full code-block API references + a 13-item config-options dump (D1) + 2 code blocks each + `>` excerpt blocks. High quality but it pastes the docs into the planner's context. Output-budget setup with large headroom.
## Experiment 1 — KEEP
**Score:** 9/10 (baseline 6/10) — E1 2/2 (must-keep docs+APIs named inline), E2 2/2 (critical gotchas: trust-proxy/MemoryStore/IPv6 for D1; v3-vs-v4/flatten-one-level for D2), E3 **0->2/2** (no code blocks, no multi-line excerpts, no option dumps), E5 2/2 (real URLs), E4 1/2 (D1 374 ✓, **D2 453 ✗** by 3 tok).
**Change:** "pointer, not a paste" budget — under ~450 tok, name the key API signature INLINE, NO fenced code blocks / multi-line excerpts, Known Issues = top 3-5 implementation-critical gotchas only (no exhaustive config-option dump — link it), omit empty sections. Dropped the `### API Quick Reference` code block from the template; updated Output Rules to "no code blocks, the link carries depth."
**Result:** D1 ~1200 → ~374 tok (~69% leaner); D2 ~870 → ~453 tok (~48% leaner). Every must-keep doc, key API (safeParse/flatten/z.infer; rateLimit({...})), and load-bearing gotcha preserved — the implementer WebFetches the link for full code/options. KEPT.
**Residual:** D2 ran 3 tok over the cap because the agent added a redundant "Key APIs (inline)" section duplicating the signatures already inline in Primary Library — a future tightening could forbid a separate signatures section. Gap-richest-input pattern (cf. flow-gap-analyst FG1): coverage > the exact cap.
