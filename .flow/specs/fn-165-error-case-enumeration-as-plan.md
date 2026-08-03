# Error-case enumeration as plan discipline

## Goal & Context
<!-- scope: business -->

Benchmark evidence (SlopCodeBench lite-opus5, 2026-08-03, gmickel/scb-flow-next; vault: "flow-next - SlopCodeBench Experiment"): every strict checkpoint the flow-next pipeline lost (4 of 17) traced to a SINGLE untested error path — a JSON error-handling case the agent never wrote a test for, which then failed the hidden suite at checkpoint 5 and, via inherited regression tests, every checkpoint after it. The paper behind the benchmark reports the same pattern generally: error-category tests drive most long-horizon decay.

The sharp lesson: **a persisted regression suite entrenches blind spots exactly as faithfully as knowledge.** "All my tests pass" every session actively signals nothing-to-fix for the cases nobody enumerated. Review can catch this late; the cheap fix is upstream, at plan time, where acceptance criteria are written.

Goal: make error/invalid-input cases a first-class, enumerated part of every spec's acceptance criteria, so the work stage inherits them as required tests instead of relying on implementer imagination.

## Architecture & Data Models
<!-- scope: technical -->

Three placement points (all prompt/template, no flowctl changes):

1. **Spec template** (`.flow/templates/spec.md` + plugin copy): the Acceptance Criteria scaffold gains an explicit negative-cases discipline — each behavioral criterion states its error/invalid-input/boundary handling, or the spec explicitly records "no error surface" for that criterion. Wording keeps it lightweight: enumerate the cases that exist, not ceremony for ones that don't.
2. **Plan skill** (flow-next-plan): during AC derivation, instruct enumeration of error/invalid/boundary cases per criterion (malformed input, missing files, conflicting state, limits) and write them INTO the ACs. Interview skill gets the matching probe question.
3. **Work skill / worker.md**: the test-writing guidance ties required tests to the spec's enumerated error cases — the regression suite must cover every enumerated case before `done`.

## Edge Cases & Constraints
<!-- scope: technical -->

- Weight discipline: this must not bloat every small spec — a one-line "no error surface beyond X" is a valid enumeration. The eval lesson from fn-99 applies: minimal inline guidance beats prose walls.
- Template changes hit the fn-99 territory (template files, possible token-budget tests, lockstep twins where they exist) — coordinate; second lander rebases.
- Existing specs are not migrated; discipline applies to new specs.
- Claude/codex skill mirrors stay in lockstep via the existing sync path.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Spec template's AC section carries the negative-cases discipline with a worked example (one criterion + its error cases + a valid "no error surface" line).
- **R2:** Plan skill derives and writes error/boundary cases into ACs; verifiable on a fixture request whose happy path is trivial but whose error surface is not (e.g. "parse a config file").
- **R3:** Interview skill asks the error-surface probe when ACs lack negative cases.
- **R4:** worker.md ties required tests to enumerated error cases; `done` guidance references them as part of verification evidence.
- **R5:** Any template token-budget tests still pass (or budgets consciously adjusted with rationale).
- **R6:** CHANGELOG entry; docs-site staged per downstream conventions.

## Boundaries
<!-- scope: business -->

- NOT a flowctl/state change — prompts, templates, and skill docs only.
- NOT retroactive spec migration.
- NOT a general test-quality rubric (test slop rules etc.) — scoped to error-case enumeration at plan time.
- NOT gated/review-stage changes — review's fresh-eyes error hunting is complementary and out of scope here.
