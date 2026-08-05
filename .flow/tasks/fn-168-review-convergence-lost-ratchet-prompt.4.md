---
satisfies: [R4, R5]
---
# fn-168-review-convergence-lost-ratchet-prompt.4 Parser-path e2e proof + docs + decision record + CHANGELOG + full gate

## Description
Prove the whole seam through the production reservation path (three required cases), then land docs, the decision record, the CHANGELOG entry, and the full final gate.

**Size:** L
**Files:** `plugins/flow-next/tests/test_review_convergence_cap.py`, `plugins/flow-next/docs/review-findings.md`, `plugins/flow-next/docs/README.md`, `plugins/flow-next/docs/troubleshooting.md`, `CHANGELOG.md`, `.flow/memory/knowledge/decisions/<new-entry>.md`

### Approach
- **Three required e2e cases, all driving the production reservation path** (`enforce_and_increment_review_cap`), not `_review_stall_rule` in isolation and not hand-built containers:
  1. **the real fn-158 pair** — round 1: 6 fresh introduced P1; round 2: those 6 resolved via the aggregate record + 1 fresh P1 → a normal round-3 reservation with **no stall of any class**. Unlike `.3`'s direct-digest proof, this one must produce the `fixed` statuses by running reviewer text through the parser that `.1`/`.2` fixed;
  2. **churn counter-case** — the same `chainRoot` at `not_fixed` in both rounds → still ESCALATEs (`same-not-fixed-lineage`);
  3. **no-grammar case** — rounds with zero resolution evidence never stall early; they are bounded only by the cap.
- **Docs** (`plugins/flow-next/docs/`):
  - `review-findings.md` (~100-121, "Identity and lineage") — state the literal per-ordinal grammar, the aggregate record, and that `unaddressed: []` is **not** a prior-findings signal;
  - `README.md` "Notable updates" — one bullet (precedent: the 3.14.0 convergence bullet ~:65);
  - `troubleshooting.md` (~:83) — update the root-cause list (a review loop that runs to the cap is now the expected shape for a non-compliant reviewer, not a bug);
  - confirm `.3` already rewrote `flowctl.md` ~:2000; if any stall-class name survives anywhere in docs, fix it here.
- **`knowledge/decisions/` entry — required, contents fixed.** The predictable failure mode is someone seeing a runaway loop in six months and reinventing `flat-trajectory`; this entry is the vaccine. It also partially retires a **shipped** spec's acceptance contract, so the supersession must be recorded. Must contain, **in this order**:
  1. **The failure-direction flip, leading:** non-compliance now produces *expensive* answers instead of *wrong* ones (before: inflated open set → false stall at round 2, a silent correctness failure forcing hand-verification; after: lineage silent → runs to the cap, a bounded, visible cost failure). Cap as the ceiling. R6 as the protection for the surviving terminal.
  2. **The historical hinge — quote `get_max_review_iterations()`'s docstring verbatim:** *"The cap counts dispatches, which cannot distinguish a loop that is genuinely stuck from one converging in severity while each fix surfaces one more small thing. Field evidence: in a single session three specs hit the cap at 4, and in every case the findings remaining were trivial residue - two were reset by a human and shipped almost immediately after."* — then close with **"the answer was better evidence, not better inference."** That same observation motivated building the heuristics; it is what now retires them.
  3. **The two transcript observations:** a plan-review round-1 tail carrying `"unaddressed":["R1","R3","R6"]` before any prior finding existed, and a round-3 SHIP tail carrying `"unaddressed":[]` with zero discussion of priors. An `unaddressed` key firing on a round where priors don't exist is what makes the "ambient, not a statement" argument unanswerable.
  4. **The empirical asymmetry:** 3 recorded false positives (fn-156/157/158) vs **0 recorded true positives** for either deleted class. **Honest caveat, required:** churn IS real — memory `pr-bot-review-loops-do-not-converge-2026-08-04` documents non-convergence in the wild — but in the **PR channel**, bounded by `land.ciFixBudget`, not by these rules. "We deleted the rules" must not read as "we decided churn is a myth."
  5. **The same-defect-class argument:** both deleted classes were round-local snapshots inferring convergence; the survivor reads an explicit statement.
  6. **Accepted consequences (a)-(d)** from the spec's Boundaries.
  7. **fn-159 R2 supersession**, named explicitly (it enumerates all three rules with exact math).
- **CHANGELOG** `## Unreleased`, outcome-first per `agent_docs/releasing.md`. **No version bump** (batched per CLAUDE.md).
- **Full gate:** `python3 scripts/run_tests_parallel.py` (serial fallback `--serial`) + `uvx ruff@0.16.0 check .` + propagation (`cp` flowctl.py → `.flow/bin/flowctl.py`, `./scripts/sync-codex.sh` twice with no second-run diff) + `test_prompt_text_pinned` green.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py` — `enforce_and_increment_review_cap` (~:10891) / `_enforce_and_increment_review_cap_locked` (~:11325) and the stall consult (~:11598): the exact production path the three cases must drive
- `plugins/flow-next/tests/test_review_convergence_cap.py` — the existing reservation-path test harness (how a consumed verdict row with a digest is produced end to end)
- `plugins/flow-next/docs/review-findings.md` (~100-121) — the "Identity and lineage" section to extend
- `agent_docs/releasing.md` — the CHANGELOG ordering rules and the hard rejection test
- `plugins/flow-next/docs/memory-schema.md` — the frontmatter contract for the decision entry

**Optional** (reference as needed):
- `plugins/flow-next/docs/README.md` ~:65 — the 3.14.0 convergence bullet as the Notable-updates precedent
- `.flow/memory/knowledge/workflow/pr-bot-review-loops-do-not-converge-2026-08-04.md` — the churn-is-real caveat's source
- `plugins/flow-next/scripts/flowctl.py` ~:9556 — the docstring to quote verbatim

### Key context
- Deps: `.2` (real `fixed` statuses from the parser path) and `.3` (the deletions). Re-anchor on both before starting — case 1 is meaningless if either is missing.
- Tests drive production paths, never parallel constructions (memory `test-production-path-not-parallel-construction-2026-05-21`).
- The old "three-round symmetry regression" wording from the pre-re-plan spec is **dead** — the symmetry concept died with the branch. Do not resurrect it.
- Both changelogs are user-facing release surfaces; write user-outcome-first, machinery last.

## Acceptance
- [ ] Case 1: the real fn-158 pair (r1 6 fresh introduced P1; r2 those 6 resolved via the aggregate record + 1 fresh P1) reaches a normal round-3 reservation with **no stall of any class**, with the `fixed` statuses produced by the production parser (not injected)
- [ ] Case 2: churn counter-case (same `chainRoot` `not_fixed` in both rounds) still ESCALATEs via the production reservation path
- [ ] Case 3: rounds with zero resolution evidence never stall early and are bounded only by the cap
- [ ] `docs/review-findings.md` states the literal grammar, the aggregate record, and the `unaddressed: []` non-signal note
- [ ] `docs/README.md` "Notable updates" bullet added; `docs/troubleshooting.md` root-cause list updated; no stall-class name survives anywhere in docs
- [ ] `knowledge/decisions/` entry written with all 7 required elements in order, including the verbatim docstring quote, the churn-is-real caveat, and the explicit fn-159 R2 supersession
- [ ] CHANGELOG `## Unreleased` entry, outcome-first; **no version bump**
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`
- [ ] Propagation verified: `.flow/bin/flowctl.py` current, `./scripts/sync-codex.sh` run twice with no second-run diff, `test_prompt_text_pinned` green

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
