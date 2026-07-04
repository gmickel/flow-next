# Autoresearch — audit (fn-84.5)

Eval-driven optimization of `/flow-next:audit` (SKILL.md + phases.md + workflow.md; ~14k tok). audit is
the **memory garbage-collector**: it classifies each `.flow/memory/` entry Keep / Update / Consolidate /
Replace / Delete (autofix ambiguity → `mark-stale`). It is **FINDER-SHAPED**, so the over-flag guard on a
clean corpus (E2) is load-bearing — a finder that invents problems on healthy memory is worse than none.

Ratchet: accuracy (E1–E3, incl. the over-flag guard) is the zero-quality-loss floor; keep iff
accuracy ≥ baseline AND (accuracy↑ OR tokens↓ OR quality↑).

## Run-trick — mode:autofix EMISSION (+ frozen codebase context)

audit investigates the codebase to classify each entry, then (in autofix) mutates via git rm / Write /
`mark-stale`. For the eval, the run-subagent reads the audit prose + the fixture memory store + a
**frozen codebase-state context** (the ground truth audit's investigation would find, held constant so
the eval isolates the classification prose) and **EMITS a per-entry verdict + one-line reason** — it does
NOT execute the mutations. Output-only; `mode:autofix` (non-interactive; no `AskUserQuestion`). Model held
constant: **sonnet**.

**Worktree-isolation mechanic (Major-1) — still DEFERRED.** audit is write-happy (git rm / Write), so this
was the candidate suite to prove the throwaway-worktree mechanic. It does NOT here: classification is the
judgment audit optimizes, and it's emission-scorable (audit decides before it writes). The deferral rolls
forward — emission has now covered plan/capture/interview/make-pr/audit; the worktree fallback has not
proven necessary (a suite would need to score the WRITTEN mutation, not the decision, to require it).

## Fixtures + over-flag

`test-inputs.md`: **M1** (7 entries, mixed — Keep/Update/Delete/Consolidate-pair/Replace/ambiguous→mark-stale,
with a frozen answer key) for classification + the consolidate-vs-delete lever; **M2** (4 accurate, current
entries) is the CLEAN corpus for the over-flag guard (all must be Keep). Answer keys are for scoring only,
never shown to the run. Synthetic entries; scrubbed (no real PII).

## Files
`test-inputs.md` · `evals.md` (E1–E3 accuracy incl. over-flag; E4 consolidate-vs-delete quality) ·
`results.tsv` · `changelog.md` · `baseline/{SKILL,phases,workflow}.md`.
