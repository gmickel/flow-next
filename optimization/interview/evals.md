# Binary evals (5) — per run max = 5; max_score = 5 × 4 inputs = 20

**Extended-schema split (fn-84):** E1–E3 are ACCURACY, host-scored (accuracy_max = 3 × 4 = **12**, the
floor). **E4–E5 are QUALITY, judged by an independent `fable` subagent** (quality_max = 2 × 4 = **8**) —
question quality is subjective, so a capable independent judge beats host-only scoring (per the user's
steer; interview is core-workflow). E4 (NFR coverage) is the quality-lever's scoring eval. **Fixture
count:** the 4th fixture (I4, restraint-stress) was added to `test-inputs.md` BEFORE the baseline row
was recorded — the eval SET (E1–E5) was frozen first, so this is Major-B-clean (no baseline existed
when I4 was added; the earlier "3 inputs" wording in this file was pre-I4).

**Ratchet:** accuracy never drops; keep iff accuracy ≥ baseline AND (accuracy↑ OR tokens↓ OR quality↑).
**E5 is ADVISORY-pending-fidelity:** fn-84.3 found E5 ("is this padding") is a ~50%-flip subjective
judgment at N≤2 on hard fixtures (baseline I3 flipped 5/5→3/5) — it **cannot gate a ratchet decision on
its own** until majority-voted at N≥5 or backed by a sealed holdout. Treat E5 as directional signal;
lean on the E1–E3 accuracy floor + E4 as the hard guards.

**What is scored:** the QUESTIONS the run emits (its would-ask set, in decision-tree order, each with a
lead recommendation + confidence tier + options). On I3, also whether it preserved the user's spec.
Same-family caveat: runs are `sonnet`, the judge is `fable` (different tier — the strongest independent
judge the toolset allows; note in README).

---

EVAL 1: Ask-vs-investigate discipline  [ACCURACY — host]
Question: Does the question set ask ONLY User-judgment-required questions (should / tradeoff / priority),
with nothing that the frozen codebase context already answers (which interview must resolve itself, not ask)?
Pass: no question asks a codebase-answerable fact the frozen context supplies (e.g. "what persistence?"
when it's stated); every question is a genuine should/tradeoff/priority call for the user.
Fail: any question re-asks a fact the frozen context already gives, or asks a "what exists / how wired"
question interview should have answered by investigation.

EVAL 2: Format contract — lead-with-recommendation + confidence tier  [ACCURACY — host]
Question: Does every emitted question lead with a recommended option + a one-sentence rationale AND carry
exactly one confidence tier (`[high]` / `[judgment-call]` / `[your-call]`), with `[your-call]` used where
the agent genuinely has no signal (not always-recommend)?
Pass: every question has a recommendation + rationale + one tier; at least the no-signal questions use
`[your-call]` rather than a manufactured recommendation.
Fail: a question omits the recommendation, omits/duplicates the tier, or manufactures a confident
recommendation where it has no basis (RLHF bravado) instead of `[your-call]`.

EVAL 3: Override-respect + scope + non-redundancy  [ACCURACY — host]  (I3 load-bearing)
Question: On I3 (existing hand-edited spec) does the run PRESERVE the user's spec — never rewriting/
renumbering it, never re-opening a DECIDED boundary — and across all inputs, do questions stay in
interview's scope (refining requirements; NOT task-breakdown / implementation-planning — plan's job)
with no two questions redundant?
Pass (I3): does not re-ask the two DECIDED boundaries; does not renumber R-IDs or rewrite hand-edits;
asks only genuine remaining gaps. Pass (I1/I2): questions stay in-scope, non-redundant.
Fail: re-opens a user-decided point, rewrites/renumbers the spec, drifts into task-breakdown, or asks
two duplicate questions.

EVAL 4: NFR coverage  [QUALITY-LEVER SCORING EVAL — judged by `fable`]
Question (to the fable judge): Given this spec's frozen context and the listed NFR gaps, does the emitted
question set adequately probe the MISSING non-functional requirements — failure/error modes, performance/
scale, security/authz (where applicable), concurrency/races, testing, migration/compat — skipping only
those the spec/context already fixes?
Pass: the questions surface the spec's real NFR gaps (a clear majority of the fixture's listed NFR gaps
are touched by a genuine question).
Fail: the question set is functionally-focused and misses the bulk of the spec's NFR gaps (e.g. no
failure-mode / concurrency / perf probing when the context makes those live).

EVAL 5: Overall question quality  [QUALITY — judged by `fable`]
Question (to the fable judge): Are the questions high-value and non-obvious — surfacing hidden complexity
and genuine ambiguities rather than trivia the user obviously knows — well-prioritized (important /
decision-gating first, decision-tree order), and free of padding?
Pass: the set reads as a sharp senior-engineer interview — non-obvious, decision-relevant, prioritized,
no filler.
Fail: obvious/low-value questions, poor prioritization, or padding to hit a count.
