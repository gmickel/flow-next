# Autoresearch changelog — github-scout (output budget: pointer-not-paste)

Lever: feature-preserving output budget. gh-backed; eval = format budget + key-source/pattern
survival. Model held: opus. 1 stable query (express-rate-limit usage), leaning on the proven
docs-scout analog.

## Experiment 0 — baseline
**Score:** 3/5 — E1 ✓ (official repo + 3 example repos + issue #502, all with ★/tier/path), E2 ✓ (ipKeyGenerator/IPv6 + trust-proxy gotcha), E5 ✓ (real gh results), **E3 ✗** (4 fenced code blocks across Authoritative + Quality Examples), **E4 ✗** (~1100 tok).
**Bloat:** a code snippet per source + a Source-Quality-Summary TABLE duplicating the ★/tier already on each repo line + Search-Queries-Used. Biggest output-budget headroom of the scout fleet.

## Experiment 1 — KEEP
**Score:** 5/5 (baseline 3/5) — E1 ✓ (express-rate-limit Tier 1 + juice-shop/sqtracker examples, all ★/tier/path/link), E2 ✓ (ipKeyGenerator/IPv6 #502 + trust-proxy #363 + per-route pattern), E3 **0->pass** (zero code blocks), E4 **0->pass** (301 tok), E5 ✓ (real repos/issues).
**Change:** pointer-not-paste budget — one line per repo (`**owner/repo** (★N, Tier T) — path: pattern named inline`), NO fenced code blocks, NO Source-Quality table (★/tier already on each line), top 2-3 repos/tier, never drop the Tier-1 source or a load-bearing pattern/gotcha, Search-Queries dump off by default.
**Result:** ~1100 → 301 tok (~71% leaner — the biggest reduction of the fleet; github-scout was the most code-heavy). All authoritative sources, example repos, patterns and gotchas preserved — and the budgeted run even surfaced an EXTRA gotcha (trust-proxy issue #363) baseline missed. The implementer opens the repo at the cited path to read the actual code. KEPT.
