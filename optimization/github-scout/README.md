# Autoresearch — github-scout (output budget: pointer-not-paste)

Eval-driven optimization of `plugins/flow-next/agents/github-scout.md` — searches GitHub for
code patterns; output flows into the planner. Biggest headroom of the scout fleet: multiple
fenced code blocks per source + a Source-Quality-Summary table that duplicates the per-repo
stars/tier already on each line (baseline ~1100 tok). Lever: feature-preserving output budget —
**pointer, not paste**: name the repo (★/tier) + path + the pattern in one line; the implementer
opens the repo to read the code. Drop code blocks + the duplicate table; cap per tier.
gh-search-backed (noisy coverage), so the eval targets the FORMAT budget + survival of the key
sources/patterns/gotchas. Light validation (1 stable query) leaning on the proven docs-scout analog.
Model held: opus.

Files: evals.md · results.tsv · changelog.md · github-scout.md.baseline
