# Autoresearch — docs-scout (output budget: pointer-not-paste)

Eval-driven optimization of `plugins/flow-next/agents/docs-scout.md` — finds framework/library docs
for a change; output flows into the planner. Baseline pastes full code blocks + exhaustive
config-option lists + multi-line excerpts (D1 ~1200 tok, D2 ~870 tok). Lever: feature-preserving
output budget — be a **pointer, not a paste**: keep WHICH docs (URLs) + the key API named inline +
the top critical gotchas; drop the code-block/excerpt/option-dump (depth is one WebFetch away at the
link). Web-backed/non-deterministic, so the eval targets the FORMAT budget + survival of the
must-keep API/gotchas (per-input answer key in test-inputs.md). Model held: opus. 2 inputs.

Files: test-inputs.md · evals.md · results.tsv · changelog.md · docs-scout.md.baseline
