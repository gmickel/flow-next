# Autoresearch changelog — context-scout

Each entry: experiment N, keep/discard, score, change, reasoning, result.
Test bed: ~/work/DocIQ-Sphere (R9). Model held constant: opus. Runs/experiment: 3 (T1,T2,T3).

## Experiment 0 — baseline
**Score:** 9/15 (60.0%)  [T1 3/5, T2 3/5, T3 3/5]
**Per-eval:** Grounded 3/3 · Coverage 3/3 · Tagged 3/3 · Lean **0/3** · Focused **0/3**
**Run path:** rp-cli unavailable for DocIQ-Sphere → all 3 took the prompt's documented Fallback (Grep/Glob/Read), as expected for a headless subagent.
**Failure pattern:** every output ~1400–1500 tok (cap 650). Causes: (1) the prescribed `### Code Signatures` fenced block — 13–15 lines every run (fails Focused's >10-line rule AND inflates tokens); (2) bold sub-headers (`**Entry / orchestration**`) + grouping prose between Key Files bullets; (3) uncapped item counts (T1 listed ~16 files across 4 sub-groups); (4) verbose multi-clause Architecture Notes + Recommendations.
**Accuracy was already maxed** — grounding (every path `test -f` verified), coverage (all per-input anchor sets hit + backend hand-off identified), and confidence tags held 3/3. The only headroom is the two token levers. Classic output-budget setup (mirrors repo-scout exp0).

## Experiment 1 — KEEP
**Score:** 14/15 (93.3%)  [T1 4/5, T2 5/5, T3 5/5]
**Per-eval:** Grounded 3/3 · Coverage 3/3 · Tagged **2/3** · Lean **3/3** (was 0/3) · Focused **3/3** (was 0/3)
**Change (one hypothesis = the output-budget lever, applied consistently):**
1. Added a hard **Output budget** block at the top of `## Output Format`: under ~500 tokens, repo-relative paths only, top 3–5 Key Files/area (≤~7 total), one line per finding (no sub-headers/grouping prose), **no fenced code blocks** (fold the load-bearing signature inline), omit empty sections.
2. **Removed the prescribed `### Code Signatures` fenced block** from the output template — the single biggest per-run bloat + the sole Focused failure (it was 13–15 lines every run). Signatures now ride inline on the Key Files / Architecture line.
3. Rewrote the "Complete Example" response + bottom "Output Rules (for planning)" so the few-shot no longer contradicts the budget (it previously demonstrated a Code Signatures block and untagged bullets).
**Reasoning:** baseline's only failures were the two token levers (Lean, Focused); both traced to the same root — the prescribed code-signature block + uncapped/sub-headered Key Files. One budget rule placed where the model formats output fixes both. Mirrors repo-scout exp1.
**Result:** every output dropped ~60–70% (T1 ~1500→~421 tok, T2 ~1400→~590, T3 ~1500→~488). Grounding held (every cited path `test -f` verified, incl. the new `vendor/docx_skill/scripts/document.py` which matches `xml_util.py:15`'s import). Coverage held 3/3 — all per-input anchor sets still hit and the backend hand-off (`agentRuns.start` + `agentRunner.schedule`) still surfaced. Bonus: the prompt itself shrank 9 lines (small input-token win every dispatch).
**Residual (for a future experiment / eval):** T1 collapsed `native-conversation.tsx` + `chat-transcript.tsx` into one line under a compound `[VERIFIED … INFERRED …]` tag — the budget's "one line per finding" nudged a 2-file merge that breaks "exactly one tag." A follow-up could add "one file per bullet" to the budget, or the Tagged eval could explicitly forbid compound tags. Did not chase it (already at 93%, accuracy intact).
