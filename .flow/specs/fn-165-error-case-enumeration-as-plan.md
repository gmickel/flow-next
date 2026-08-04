# Error-case enumeration as plan discipline

## Goal & Context
<!-- scope: business -->

Benchmark evidence (SlopCodeBench lite-opus5, 2026-08-03, gmickel/scb-flow-next; vault: "flow-next - SlopCodeBench Experiment"): every strict checkpoint the flow-next pipeline lost (4 of 17) traced to a SINGLE untested error path — a JSON error-handling case the agent never wrote a test for, which then failed the hidden suite at checkpoint 5 and, via inherited regression tests, every checkpoint after it. The paper behind the benchmark reports the same pattern generally: error-category tests drive most long-horizon decay.

The sharp lesson: **a persisted regression suite entrenches blind spots exactly as faithfully as knowledge.** "All my tests pass" every session actively signals nothing-to-fix for the cases nobody enumerated. Review can catch this late; the cheap fix is upstream, at plan time, where acceptance criteria are written.

Goal: make error/invalid-input cases a first-class, enumerated part of every spec's acceptance criteria, so the work stage inherits them as required tests instead of relying on implementer imagination.

## Architecture & Data Models
<!-- scope: technical -->

Three placement points (all prompt/template, no flowctl changes). Verified current state (HEAD): none of the four edit targets appears in `test_prompt_text_pinned.py`'s `TEMPLATE_HASHES`/pinned-constant sets (that suite also pins review templates and embedded flowctl prompt constants — just not these files) and none are token-budget-pinned (`test_token_budgets.py` pins `claude-md-snippet*.md` + `usage.md` only) — no hash churn expected; the tasks assert this stays true. NOTE: `templates/spec.md` DOES have a codex-mirror byte-equality guard (`test_template_canonical.py` + `test_dogfood_template_parity`) — every task that edits a mirrored canonical file runs `./scripts/sync-codex.sh` twice and commits the mirror in the SAME task.

1. **Spec template** (`plugins/flow-next/templates/spec.md:97-113` AC section; `.flow/templates/spec.md` setup-managed copy regenerated in the same change): the Acceptance Criteria scaffold gains the negative-cases discipline — each behavioral criterion states its error/invalid-input/boundary handling INSIDE the R-ID bullet (sub-clauses or sub-bullets, NOT new sub-R-IDs, NOT new coverage-table columns), or explicitly records "no error surface beyond X" for that criterion. One compact worked example inline (2-3 lines: one criterion + its error cases + one valid no-error-surface line); the longer explanation lives in `docs/spec-template.md`.
2. **Plan skill** (`flow-next-plan`): the AC-derivation guidance (`steps.md:427-433` R-ID rule block + the scaffold heredoc `:341-411` + `SKILL.md:226` one-liner) instructs enumerating error/invalid/boundary cases per criterion (malformed input, missing files, conflicting state, limits) and writing them INTO the ACs; `examples.md` gets one good/bad error-case example. Interview skill: the AC bucket (`questions-technical.md:67-72`) gains the error-surface probe — asked when the drafted/existing ACs lack negative cases (interview already reads the spec; this is a judgment instruction, no new mechanism).
3. **Work skill / worker.md**: the test-writing rule (`agents/worker.md:279` "Add tests if spec requires them") extends to: required tests must cover every error case enumerated in the ACs the task satisfies; `done` summary/evidence references them. Soft guidance — no gate or receipt change.

## Edge Cases & Constraints
<!-- scope: technical -->

- Weight discipline: a one-line "no error surface beyond X" is a valid, complete enumeration — the template example shows it so small specs don't bloat. Minimal inline guidance beats prose walls (fn-99 lesson: guidance placement determines behavior).
- "Considered and declared none" vs "forgot": the discipline's whole point — an R-ID with neither error clauses nor a no-error-surface line is visibly incomplete to plan-review's fresh eyes, without any new review-stage machinery (review changes stay out of scope).
- G-ID interplay: repos with `.flow/criteria.md` don't restate standing criteria; the error discipline applies to what the spec ADDS (its own R-IDs), same as the existing G-ID rule in plan steps.md.
- Mid-flight specs: worker.md wording scopes the test-tie to "error cases enumerated in the ACs" — a pre-discipline spec with none enumerated triggers nothing (no spurious gate friction; not retroactive).
- Codex mirrors: all four targets are mirrored (worker.md → worker.toml); `./scripts/sync-codex.sh` twice; new Claude-only phrasing may need a transform + guard.
- Renaming/restructuring `## Acceptance Criteria` is forbidden (parsers depend on it) — additions go under the existing heading.
- Overlap: fn-163/fn-164 also touch worker.md (different sections); second lander rebases.

## Decision context
<!-- scope: technical -->

- Error cases fold INTO the parent R-ID bullet (prose sub-clauses/sub-bullets), not sub-R-IDs and not a new coverage-table column: keeps the R-ID grammar, coverage table, and every downstream parser untouched, and keeps small specs light. The template's existing letter-suffix convention (R4a) remains available for genuinely separable criteria, unchanged.
- R2 verification is a documented fixture walkthrough, not an eval harness: run `/flow-next:plan` (or dry-compose its AC step) on the fixture request "parse a config file" and show the derived ACs enumerate malformed-file/missing-file/limit cases; evidence goes in the task's done summary. An agent-evals study is explicitly NOT required (fn-99 established the eval discipline for token-budget claims; this is a presence/behavior claim).
- Interview probe lives in the AC bucket (questions-technical.md:67-72) rather than the general Error Handling bucket (:25-30) — the probe is specifically about AC completeness, and the general bucket already covers system-level failure modes.

## Strategy Alignment

Active tracks served by this plan:
- **Spec-driven team patterns** — extends the R-ID methodology with a negative-cases discipline at the same place the methodology already concentrates its leverage: plan-time acceptance criteria that downstream work/review stages inherit.

## Quick commands
```bash
cd plugins/flow-next/tests && python3 -m unittest test_token_budgets test_prompt_text_pinned -q
```
(Final gate: full parallel suite + `uvx ruff@0.16.0 check .` + sync-codex.sh twice, per repo CLAUDE.md. No flowctl.py change → no .flow/bin propagation.)

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Spec template's AC section carries the negative-cases discipline with a compact worked example (one criterion + its error cases + a valid "no error surface" line); `.flow/templates/spec.md` copy regenerated in the same change; `## Acceptance Criteria` heading and R-ID grammar unchanged.
- **R2:** Plan skill derives and writes error/boundary cases into ACs; verified by a documented fixture walkthrough on a request whose happy path is trivial but whose error surface is not (e.g. "parse a config file"), with the walkthrough evidence in the task's done summary.
- **R3:** Interview skill asks the error-surface probe when ACs lack negative cases (AC bucket, judgment-triggered; accepts a one-line "no error surface" answer without escalating).
- **R4:** worker.md ties required tests to the error cases enumerated in the ACs the task satisfies; `done` guidance references them as verification evidence; specs with none enumerated trigger nothing.
- **R5:** `test_token_budgets.py` and `test_prompt_text_pinned.py` still pass unchanged (verified: none of the four targets are pinned; if that assumption breaks, adjust consciously with rationale in the commit).
- **R6:** CHANGELOG `## Unreleased` entry; docs-site staged per downstream conventions; `docs/spec-template.md` documents the convention; no version bump (batched releases).

## Early proof point
Task fn-165-error-case-enumeration-as-plan.1 validates the core approach (template discipline + worked example that stays lightweight). If the inline example can't stay compact without losing clarity, re-evaluate placement (template vs docs split) before propagating the discipline into three skills.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Template discipline + worked example + copy regen | .1 | — |
| R2  | Plan skill enumeration + fixture walkthrough | .2 | — |
| R3  | Interview error-surface probe | .2 | — |
| R4  | worker.md test-tie | .2 | — |
| R5  | Pinning/budget tests unchanged | .1, .2 | — |
| R6  | CHANGELOG + docs-site + spec-template docs | .1 (docs), .2 (CHANGELOG + mirrors) | — |

## Boundaries
<!-- scope: business -->

- NOT a flowctl/state change — prompts, templates, and skill docs only.
- NOT retroactive spec migration; mid-flight specs with no enumerated cases trigger nothing.
- NOT a general test-quality rubric (test slop rules etc.) — scoped to error-case enumeration at plan time.
- NOT gated/review-stage changes — review's fresh-eyes error hunting is complementary and out of scope here (plan-review benefits passively from visible gaps, with zero prompt changes).
- NOT new R-ID grammar, sub-R-IDs, or coverage-table columns.
