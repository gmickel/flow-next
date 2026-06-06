# Autoresearch — practice-scout (output budget: pointer-not-paste)

Eval-driven optimization of `plugins/flow-next/agents/practice-scout.md` — finds best-practice
do/don't + examples for a change; output flows into the planner. Most verbose scout (Do×8 / Don't×5
/ Examples-with-code-block / Security / Performance / Source-Quality / Sources×9 ≈ 1300 tok). Lever:
feature-preserving output budget — pointer not paste: one line per do/don't (practice + why + inline
source link), no code blocks, cap items, drop the redundant bottom Sources section (sources ride
inline). Cap 600 tok (broader scope than docs-scout's 450). Web/gh-backed; eval = format budget +
survival of load-bearing practices/pitfalls. Light validation (1 stable query), proven docs/github
analog. Model held: opus.

Files: evals.md · results.tsv · changelog.md · practice-scout.md.baseline
