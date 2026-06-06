# Autoresearch changelog — practice-scout (output budget: pointer-not-paste)

Lever: feature-preserving output budget. Web/gh-backed; eval = format budget + practice/pitfall
survival. Cap 600 tok. Model held: opus. 1 stable query (IP rate-limiting best practices).

## Experiment 0 — baseline
**Score:** 3/5 — E1 ✓ (do/don't all load-bearing), E2 ✓ (pitfalls), E5 ✓ (real 2025/26 sources + confidence calibration), **E3 ✗** (rate-limit-redis code block), **E4 ✗** (~1300 tok).
**Bloat:** Do×8 + Don't×5 each multi-line with inline source links, Examples with a code block, Security×3, Performance×3, Source-Quality notes, AND a bottom Sources×9 section that RE-LISTS the inline links. High quality but ~3x a planner-useful budget.

## Experiment 1 — KEEP
**Score:** 4/5 (baseline 3/5) — E1 ✓ (trust-proxy/ipKeyGenerator/shared-store/headers + a CVE pin), E2 ✓ (spoofing/port-bypass/MemoryStore/Redis-fail/IP-alone), E3 **0->pass** (no code blocks), E5 ✓ (real sources + confidence calibration), **E4 ✗** (638 tok, 38 over the 600 cap).
**Change:** pointer-not-paste budget — one line per Do/Don't (practice + why + inline source), NO code blocks, Real-World Examples named (repo+what-it-shows+link, no snippet), top ~5/~5/~3/~3, **dropped the redundant trailing Sources section** (sources ride inline), Source-Quality to 1-2 lines.
**Result:** ~1300 → 638 tok (~52% leaner); every load-bearing practice + pitfall preserved, and the budgeted run even surfaced a CURRENT advisory (CVE-2026-30827) baseline missed. Lands 38 tok over the cap — practice-scout legitimately covers the most dimensions (Do/Don't/Security/Performance); per the lean↔exhaustive lesson (cf. flow-gap-analyst FG1, docs-scout D2), coverage wins over the exact cap rather than dropping a real practice. KEPT.
