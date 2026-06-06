# Autoresearch — flow-gap-analyst (Tier 1 plan-scout, R4)

Eval-driven optimization of `plugins/flow-next/agents/flow-gap-analyst.md` — a **plan-scout** whose
gap analysis flows into the planner on every `/flow-next:plan`. Its output is **uncapped free-form**
(8 sections, unbounded item counts, multi-line per-gap prose) with **no output budget** — the same
shape that made repo-scout/context-scout big output-budget wins.

**Lever: output budget — but feature-preserving.** The non-negotiable rule (per Gordon's "always be
sure we didn't lose features"): **trim per-gap VERBOSITY, never reduce the NUMBER of gaps.** Fewer
gaps = lost coverage = lost features. So the budget caps prose-per-gap (one line each, no padding),
NOT the gap count. The **Coverage eval is the feature-preservation guarantee** — it scores against a
per-input answer key of must-find critical gaps; a mutation that drops any is reverted.

**Run-trick:** a read-only `Explore`/`general-purpose` subagent reads the prompt-under-test (baseline
backup vs live) and analyzes a frozen, deliberately-underspecified feature request. Model held at
`opus`. Inputs are self-contained feature requests with known gap answer keys (gap coverage is about
the feature's flows, not repo files — so no specific repo is required; the agent may reference
patterns generically).

3 frozen inputs (varied domains): FG1 public share-link · FG2 CSV export · FG3 undo bulk-delete.

Files: test-inputs.md · evals.md · results.tsv · changelog.md · flow-gap-analyst.md.baseline
