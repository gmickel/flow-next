# Autoresearch — capture (Accuracy-critical, R5)

Eval-driven optimization of `/flow-next:capture` (skill across SKILL.md + workflow.md + phases.md,
~15k tokens). Lever per fn-54/FLOW-5 R5: **accuracy-first, token second** — `spec.md` is
USER-AUTHORITATIVE, so the evals measure *fidelity + source-tagging + read-back + no-silent-overwrite*,
NOT "is capture's spec the right spec." A token-trim is kept only if it holds every accuracy eval
(the ratchet is the guarantee — R3).

**Run-trick = `mode:autofix` (no `--yes`).** That mode is non-interactive, writes nothing, but still
runs the full synthesis and **prints the read-back payload** (Conversation Evidence + every section +
source-tag tally) to stdout, and still **hard-errors (exit 2) on the duplicate/overwrite guard**.
So a read-only `Explore`/`general-purpose` subagent told to "read SKILL.md and follow it in
mode:autofix on this frozen conversation" produces exactly the artifact the accuracy evals score —
with zero side effects. Baseline reads `optimization/capture/baseline/SKILL.md`; experiments read the
live `plugins/flow-next/skills/flow-next-capture/SKILL.md`. The canonical spec template is supplied to
the subagent by absolute path (held constant across rounds).

capture is conversation→spec (repo-agnostic for its core synthesis), so frozen inputs are **frozen
conversation transcripts**, not a repo (R9's representative-repo rule targets code-aware scouts, not
plain capture). 3 inputs: C1 clean technical (no biz signals) · C2 biz-signal-rich · C3 the
**override/collision** scenario (existing user-edited spec, invoked WITHOUT `--rewrite` → must refuse).

Files: test-inputs.md · evals.md · results.tsv · changelog.md · baseline/{SKILL,workflow,phases}.md
