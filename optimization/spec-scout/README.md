# Autoresearch — spec-scout (plan-scout, output budget)

Eval-driven optimization of `plugins/flow-next/agents/spec-scout.md` — a plan-scout that finds
relationships between a new plan and existing specs (output flows into /flow-next:plan). Output is
uncapped, no budget; the main bloat is the **"No Relationship" enumeration** (lists every unrelated
spec — pure noise that scales with the spec count). Lever: feature-preserving output budget — keep
every REAL relationship (Dependencies / Reverse-deps / Overlaps = the load-bearing output), collapse
the No-Relationship enumeration to a count, one line per relationship.

Run-trick: subagent reads the prompt-under-test + the frozen inline open-specs corpus (in
test-inputs.md), no flowctl/web. Model held: claude-sonnet-4-6. 2 inputs (API+auth / events).
Feature-preservation = the per-input relationship answer key (must-surface deps/overlaps).

Files: test-inputs.md · evals.md · results.tsv · changelog.md · spec-scout.md.baseline
