# Autoresearch — prospect (fn-84.6)

Eval-driven optimization of `/flow-next:prospect` (SKILL.md + workflow.md + personas.md). prospect generates
candidate ideas, then **Phase 3 Critique** rejects what doesn't belong — `{verdict: keep|drop, taxonomy,
reason}` per candidate against a FIXED 7-slug taxonomy, with a **≥40% rejection floor**. Critique is BLIND
(snapshot + candidates only; no focus hint / personas — anti-sycophancy). It's a REJECTER, so the over-reject
guard (E2, a mostly-good batch below the floor) is load-bearing.

Ratchet: accuracy (E1–E3, incl. the over-reject guard) is the zero-quality-loss floor; keep iff
accuracy ≥ baseline AND (accuracy↑ OR tokens↓ OR quality↑).

## Process (fn-84.5 lesson): fable-review the eval DESIGN BEFORE the runs
The fixtures/keys/evals were adversarially reviewed by a `fable` subagent BEFORE any baseline run — checking
facts-not-conclusions (the snapshot states repo FACTS, never the verdict), every candidate scored, answer
keys match the REAL taxonomy semantics, thresholds have teeth, and the fixtures stress real judgment.

## Run-trick — Phase-3 EMISSION at sonnet
The run-subagent runs ONLY the blind Phase-3 critique prompt (grounding snapshot + candidate list) and EMITS
`{id, verdict, taxonomy, reason}` per candidate + the computed rejection rate / floor state. It does NOT
generate candidates, ground the repo, or write an artifact. Non-interactive (the floor question is reported,
not asked). Model held constant: **sonnet** (the judgment tier).

## Fixtures + over-reject guard
`test-inputs.md`: **C1** (9 candidates, mixed — one per taxonomy slug + 3 grounded keeps, facts-only snapshot,
frozen answer key) for classification + taxonomy precision; **C2** (6 candidates, mostly-good, below the 40%
floor) is the over-reject guard — the critique must keep the 5 good + report the floor unmet, never fabricate
rejections. Synthetic; scrubbed.

## Files
`test-inputs.md` · `evals.md` (E1–E3 accuracy incl. over-reject; E4 taxonomy-precision quality) · `results.tsv`
· `changelog.md` · `baseline/{SKILL,workflow,personas}.md`.
