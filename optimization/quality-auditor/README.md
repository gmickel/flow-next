# Autoresearch — quality-auditor (uncapped free-form agent, output budget)

Eval-driven optimization of `plugins/flow-next/agents/quality-auditor.md` — a code-review agent whose
findings report is **uncapped free-form** (per-finding Risk/Fix prose, What's Good, no token budget).
Lever: **feature-preserving output budget** — trim per-finding verbosity, **NEVER drop a finding or
weaken a severity/confidence** (a missed bug = a lost feature).

**Frozen input = the slop-testbed** (`~/work/slop-testbed`, answer key at
`~/work/agent-scripts/slop-testbed-answer-key.md`): `slop-feature.diff` (169 lines, 7 known planted
issues incl. #6 a Major fake-success error-swallow bug + structural slop #1/#2/#4/#5/#7) and
`clean-feature.diff` (80 lines, no issues — the false-positive control). Frozen in `fixtures/`.

**Run-trick:** a read-only subagent reads the prompt-under-test and reviews the provided diff (no
git). Model held at `opus`. The slop-testbed IS the feature-preservation eval: the budgeted reviewer
must still catch every finding baseline caught (esp. the Major bug) AND stay quiet on clean.

Files: evals.md · results.tsv · changelog.md · quality-auditor.md.baseline · fixtures/{slop,clean}.diff
