# Binary evals (5) — per run max = 5; max_score = 5 × 4 inputs = 20

**Split (extended-schema, fn-84 Major-3):** E1–E4 are ACCURACY (accuracy_max = 4 × 4 = **16**);
E5 is a dedicated QUALITY-lever scoring eval (quality_max = 1 × 4 = **4**). All 5 evals are
authored here, in the finalized suite, **BEFORE baseline** (Major-B: baseline and every experiment
are scored under this SAME eval set; adding an eval later forces a fresh baseline row). A
quality-lever experiment may target whichever pre-authored eval the baseline shows headroom on (E3
or E5); the specific pivot chosen and its rationale are recorded in `changelog.md` (exp 0), not here —
this file stays a stable statement of the eval set.

**Ratchet (per experiment) — correct hill-climb, `accuracy_score` is the zero-quality-loss floor:**
`accuracy_score` must NEVER drop. Keep a mutation iff `accuracy_score ≥ baseline` **AND at least
one improves**: `accuracy_score` rises (a correctness/quality win) OR `tokens_after < tokens_before`
(efficiency) OR `quality_score` rises (the E5 lever). Else revert. (An accuracy-raising mutation that
costs a few tokens IS kept — a correctness gain is a quality gain; the earlier "tokens-down-OR-
quality-up only" wording would have wrongly reverted it.) Every axis audits directly from `results.tsv`.

All evals are yes/no, scored by host judgment against the explicit pass condition, per input.
"Emitted spec" = the spec + tasks the run-subagent outputs (it writes nothing; README § run-trick).

---

EVAL 1: R-ID coverage on acceptance criteria  [ACCURACY]
Question: Does every acceptance criterion in the emitted spec carry a `- **Rn:**` prose-prefix
R-ID, numbered validly (sequential for a new spec; PRESERVED — never renumbered — for P3)?
Pass: every AC line is `- **Rn:** …`; new specs number R1,R2,… in order; P3 keeps R1/R2/R4/R7 exactly.
Fail: any untagged AC, an AC numbered ad-hoc, or (P3) any existing R-ID renumbered/compacted.

EVAL 2: Requirement-coverage completeness  [ACCURACY]
Question: Does the emitted spec include a `## Requirement coverage` table that maps EVERY R-ID to
≥1 task OR a stated gap justification, with no R-ID silently unmapped?
Pass: a coverage table exists; every R-ID from the Acceptance Criteria appears as a row mapped to a
task id or an explicit "Deferred/Gap" justification.
Fail: no coverage table, or ≥1 R-ID missing from it, or a row mapped to a task that doesn't exist.

EVAL 3: Task sizing (no un-split L)  [ACCURACY]
Question: Is every emitted task an S or M — files ≤ ~5 AND acceptance ≤ ~5 AND single-subsystem —
with any genuinely large unit split into M tasks rather than left as one L?
Pass: no task spans 5+ files AND 5+ AC AND multiple subsystems; large work is split.
Fail: any task is an un-split L (5+ files and 5+ AC and cross-subsystem), or over-split into
trivial sequential S fragments that should be one M.

EVAL 4: Respects user override / spec.md USER-AUTHORITATIVE  [ACCURACY] — the Major-4 guard
Question: On P3 (existing hand-edited spec), does the plan PRESERVE the user's spec — existing
R-IDs not renumbered, the hand-edited no-compression boundary kept verbatim, the R-ID gap
(no R3/R5/R6) not compacted, no fabricated requirement added as if user-authored?
Pass (P3): R1/R2/R4/R7 preserved as-is; hand-edited boundary intact; new tasks map to existing
R-IDs; no silent overwrite/renumber.
Pass (P1, P2): no existing spec in the input → trivially satisfied (new spec authored cleanly).
Fail: P3 renumbers R-IDs, compacts the gap to R1–R4, drops/rewrites the hand-edited boundary, or
invents a new requirement presented as the user's.

EVAL 5: Dependency-ordering correctness  [QUALITY-LEVER SCORING EVAL — the lever targets this]
Question: Do the emitted tasks declare a dependency structure that (a) is a valid DAG (no cycle),
(b) has NO missing edge where a task consumes another task's output (e.g. a tests/docs task that
needs the implementation task, or a task reusing a helper another task creates), AND (c) names a
correct first/early task (the one with no unmet dependency that the rest build on)?
Pass: dependencies form a valid DAG; every real "B needs A's output" edge is declared; the
early/first task is correctly identified (or, for a single-task plan, trivially satisfied).
Fail: a missing edge (a task that clearly needs another's output has no `depends_on`), a cycle, a
spurious edge forcing false serialization, or a wrong/omitted early-task call.
