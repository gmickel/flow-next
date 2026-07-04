# Autoresearch — interview (fn-84.3)

Eval-driven optimization of `/flow-next:interview` (skill: `SKILL.md` + `questions-{shared,technical,
business}.md`; technical-scope loaded set ~12.3k tokens). interview is a **core-workflow, spec.md-
authoritative, question-asking** skill — it interviews the user to refine a spec. The thing worth
optimizing (per the user's steer) is **question quality**, so the two quality evals (E4 NFR coverage,
E5 overall quality) are judged by an **independent `fable` subagent**, not host-only.

Ratchet: accuracy (E1–E3, host) is the zero-quality-loss floor; keep iff accuracy ≥ baseline AND
(accuracy↑ OR tokens↓ OR quality↑ from the fable judge).

## Run-trick — question EMISSION (+ frozen research)

interview's live contract is to ask via `AskUserQuestion`, one turn at a time, adapting to answers. For
a deterministic, scorable eval the run-subagent instead **EMITS the questions it would ask** — the full
first-pass set, in decision-tree order, each with its lead recommendation + confidence tier + options —
and does NOT wait for answers or write the spec. Codebase investigation is **frozen** (each fixture
supplies the context interview's investigate-before-asking pass would find), held constant so the eval
isolates the question-generation prose. This is output-only emission — no worktree needed.

**Worktree-isolation mechanic (Major-1/C) — STILL DEFERRED.** fn-84.1 flagged interview (or audit) as
the suite that must prove the throwaway-worktree write mechanic. It does NOT, here: question quality is
an emission-scorable output (interview asks before it writes), so emission suffices and is more
deterministic. The deferral rolls forward — a suite that scores a WRITTEN side-effect (e.g. audit's
memory mutations, if scored via the real write) is where the worktree mechanic would finally be needed.
Finding so far: output-only emission has covered plan, capture, and interview — the worktree fallback
has not yet proven necessary.

## The fable-judge protocol (E4, E5)

After each run emits its questions, a separate `fable` subagent receives (the spec + frozen context +
the fixture's NFR-gap list + the emitted questions + the E4/E5 rubric) and returns a binary PASS/FAIL +
one-line rationale per eval. The judge is blind to which prose variant (baseline vs mutated) produced
the questions. **Same-family caveat:** interview runs at `sonnet`, the judge at `fable` — different tiers,
the strongest independent judge the (all-Anthropic) toolset allows; a truly cross-vendor judge is out of
reach, so treat E4/E5 as capable-but-not-bias-free and lean on the accuracy floor (E1–E3) as the hard guard.

## Anti-overfit + override (Major-2 / Major-4)

I2 is a **non-flow-next** fixture (DocIQ-Sphere FastAPI/OOXML) — a kept change must ask good questions on
foreign code. I3 is an **existing hand-edited spec** — interview must refine without rewriting/renumbering
it or re-opening a user-DECIDED boundary (E3).

## Files

`test-inputs.md` (4 fixtures + frozen context) · `evals.md` (E1–E3 host accuracy, E4–E5 fable quality) ·
`results.tsv` (extended schema) · `changelog.md` · `baseline/{SKILL,questions-*}.md`.

## Resume

Read `changelog.md`. To re-run: reset live interview prose to `baseline/`, apply one mutation, emit
questions for the 4 fixtures at `sonnet`, fable-judge E4/E5, host-score E1–E3, append a row.
