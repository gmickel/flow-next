# fn-84 Prose optimization pass, Tier A: eval-gated autoresearch loops on 8 artifact-producing skills

## Goal & Context

fn-81/fn-82 cut runtime re-emission and always-loaded weight but deliberately banned prompt REWRITES. This spec is the third lever: rewording the live instruction prose itself — per skill, under the eval-gated autoresearch ratchet (`agent_docs/optimizing-skills.md`), scoring BOTH axes every experiment. A mutation is kept iff it improves efficiency OR quality without regressing the other. **Hard constraint (user-set): zero quality loss — the ratchet + revert discipline is the enforcement mechanism, and it is only as real as the eval suites, so suite quality is a first-class deliverable here.**

Tier A = the 8 skills whose output is a judged ARTIFACT (spec, plan, PR body, findings, report) where frozen-input + binary-eval scoring is meaningful and affordable: `plan`, `capture`, `interview`, `make-pr`, `audit`, `prospect`, `qa` (its prose surfaces: scenario derivation + bug-filing), `strategy`. Excluded: the review skills (already optimized in the fn-74 review-prompt work: impl 7→10/10 at −27% tok, plan-review 8.0→9.3) and Tiers B/C (fn-85).

Quality is an explicit agenda, not a side effect: each skill's loop includes ≥1 targeted QUALITY-lever experiment aimed at a diagnosed blind spot (the fn-74 pattern — a lean 4-item block bought plan-review 8.0→9.3 for +74 tok; broad lists lost twice). Known candidate blind spots to test: plan's task-ordering weakness (P6 never cracked), capture's `[inferred]`-tagging discipline, interview's NFR coverage, make-pr's "Where to look" reviewer-focus quality.

## Architecture & Data Models

Per-skill loop (one task per skill, identical shape):

1. **Suite** — reuse where it exists (`optimization/capture/`, `optimization/make-pr/`); else BOOTSTRAP from real `.flow/` history: frozen inputs drawn from this repo's 80+ real specs/tasks/sessions (e.g. plan gets 3-5 real spec bodies of varied size; interview gets real Q&A transcript shapes; audit gets real memory stores). 3-6 binary evals per suite, ≥2-3 of them ACCURACY evals (grounded/coverage/override-respect per optimizing-skills.md "Accuracy guard" + "spec.md is USER-AUTHORITATIVE"). Suites live at `optimization/<skill>/` with the standard files (README, evals.md, test-inputs or fixtures, results.tsv, baseline backup).
2. **Baseline** — run the skill via the subagent-reads-prompt mechanic (read-only agent given the live skill files as its operating instructions, frozen input, model held constant) N times; score; record `results.tsv` row 0. NEVER mutate before the baseline row exists.
3. **Experiments** — one mutation at a time: (a) prose trims (collapse verbose rationale, cut redundant examples, sharpen imperatives — the review-prompt "conciseness principle"); (b) ≥1 quality lever (targeted lean checklist/block at a diagnosed blind spot); (c) over-flag guard for any "find X" lever (clean-corpus run — finding-rate ≈ baseline, false-missing = 0).
4. **Ratchet** — keep iff score ≥ baseline on accuracy AND (tokens down OR quality up); revert otherwise; EVERY experiment (kept or discarded) gets a `results.tsv` row + an `agent_docs/optimization-log.md` row.
5. **Constraints carried from prior findings (binding):** proximity is load-bearing (never relocate routing/taxonomy/guardrail tables from their consuming phase); verbatim repetition at action sites is load-bearing (dedupe explanatory blocks only); less-is-more for quality levers (lean targeted beats broad — twice proven).

Ordering (frequency-weighted): `plan` → `capture` → `interview` → `make-pr` → `audit` → `prospect` → `qa` → `strategy`. capture + make-pr already have suites (fastest starts); they also just changed in fn-82 — their existing baselines must be RE-RUN on current main before any mutation.

## API Contracts

No flowctl changes. Skill-markdown-only mutations. All machine-parsed markers (verdict tags, receipts, terminal-line grammars, `Classification counts:` etc.) are FROZEN — any experiment touching one is invalid by construction. sync-codex mirror regenerated once per landed task.

## Edge Cases & Constraints

- A skill whose baseline is already at ceiling (capture was 15/15) gets trim-that-holds experiments only — no invented quality levers for their own sake ("where it makes sense" = diagnosed blind spot, not decoration).
- Suites bootstrapped from history must scrub anything private and freeze inputs (copies, not live refs) so re-runs are stable.
- Model constancy: all runs of one suite use the same model tier; note it in the suite README.
- interview/capture/plan consume or produce USER-AUTHORITATIVE spec.md — every suite for them carries the override-respect eval (hand-edited spec preserved; refusal paths intact).
- fn-83 does not overlap Tier A files (work/worker are Tier B) — fn-84 is sequence-independent of fn-83, but any suite built while fn-83 is in flight must baseline against merged main.
- Time-box per skill: if a suite can't reach trustworthy binary evals within the task budget, STOP, log why, and reclassify that skill to fn-85's conservative track — never ship a weak-eval "ratchet".

## Acceptance Criteria

- **R1:** Every Tier-A skill has a committed suite at `optimization/<skill>/` with ≥2-3 accuracy evals; bootstrapped inputs are frozen copies from real history.
- **R2:** Baseline rows recorded before any mutation, per skill (capture/make-pr re-baselined on current main).
- **R3:** Every kept mutation shows accuracy held/raised in results.tsv; every discard is logged with the regression that killed it. Zero kept mutations with an accuracy drop (ratchet integrity — audit the tsv in the PR).
- **R4:** ≥1 quality-lever experiment attempted per skill (kept or honestly discarded), targeting a diagnosed blind spot; over-flag guard run for any finder-shaped lever.
- **R5:** Proximity/repetition/marker-freeze constraints respected (spot-checked in review; no relocated consuming-phase tables).
- **R6:** `agent_docs/optimization-log.md` rows for every experiment; `optimizing-skills.md` target map updated at the end (Tier A now done).
- **R7:** Net effect table in the PR body: per skill — always-loaded tokens before/after, accuracy score before/after, quality levers kept.
- **R8:** Mirror regenerated once per landed task; smoke + full pytest green; CHANGELOG under `## Unreleased`; no version bump (batched).
- **R9:** Any skill reclassified out (weak evals) is explicitly listed with rationale — silent scope-shrink forbidden.

## Boundaries

- Review skills (impl-review, plan-review, spec-completion-review) OUT — already optimized; their rubrics only change via the review-prompt harness.
- Tier B/C skills OUT (fn-85). Agent files OUT (already budgeted).
- No structural moves (that was fn-82) — this spec rewords in place.
- No new skills/commands/flags; no flowctl changes.
- Machine-parsed markers and receipt grammars frozen.

## Decision Context

Per-skill autoresearch chosen over a bulk rewrite because rewording live judgment prose is exactly the mutation class that silently degrades quality — the ratchet converts "we think it's fine" into "the eval held". History-bootstrapped suites chosen over hand-authored corpora after costing: the repo's own specs/tasks are realistic frozen inputs at near-zero authoring cost, and eval realism dominates suite value. The explicit quality agenda (blind-spot levers) is the fn-74 lesson generalized: quality wins come from LEAN additions at diagnosed misses, and they compose with trims (both axes, same loop). The time-box + reclassify rule exists because a ratchet with weak evals is worse than no ratchet — it launders regressions as "passed".
