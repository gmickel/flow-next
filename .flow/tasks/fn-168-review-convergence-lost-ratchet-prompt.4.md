---
satisfies: [R4, R5, R8]
---
# fn-168-review-convergence-lost-ratchet-prompt.4 Parser-path e2e proof + docs + decision record + CHANGELOG + full gate

## Description
Prove the whole seam through the production reservation path (three required cases), then land docs, the decision record, the CHANGELOG entry, and the full final gate.

**Size:** L
**Files:** `plugins/flow-next/tests/test_review_convergence_cap.py`, `plugins/flow-next/docs/review-findings.md`, `plugins/flow-next/docs/README.md`, `plugins/flow-next/docs/troubleshooting.md`, `CHANGELOG.md`, `.flow/memory/knowledge/decisions/<new-entry>.md`

### Approach
- **Four required e2e cases, all driving the production reservation path** (`enforce_and_increment_review_cap`), not `_review_stall_rule` in isolation and not hand-built containers:
  1. **the real fn-158 pair** — round 1: 6 fresh introduced P1; round 2: those 6 resolved via the aggregate record + 1 fresh P1 → a normal round-3 reservation with **no stall of any class**. Unlike `.3`'s direct-digest proof, this one must produce the `fixed` statuses by running reviewer text through the parser that `.1`/`.2` fixed;
  2. **churn counter-case** — the same `chainRoot` explicitly marked `not-fixed` in **both** rounds → still ESCALATEs (`same-not-fixed-lineage`);
  3. **no-grammar case** — rounds with zero resolution evidence never stall early; they are bounded only by the cap;
  4. **R8 asymmetric case** — one explicit `not-fixed` in round 2, then a round 3 that omits it entirely (or resolves it in prose) → **no stall**. This is the case that would escalate without R8's carried-status reset, and it is the reason the survivor's "reads a statement" claim is now literally true.
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
- Deps: `.2` (real `fixed` statuses from the parser path + the R8 reset), `.3` (the deletions), and `.5` (added at plan-review round 1 — `.5` changes `flowctl.py`, the schema, the guard, and docs, so a full gate that ran before it would not be the promised final gate). Re-anchor on all three before starting.
- Tests drive production paths, never parallel constructions (memory `test-production-path-not-parallel-construction-2026-05-21`).
- The old "three-round symmetry regression" wording from the pre-re-plan spec is **dead** — the symmetry concept died with the branch. Do not resurrect it.
- Both changelogs are user-facing release surfaces; write user-outcome-first, machinery last.

## Acceptance
- [ ] Case 1: the real fn-158 pair (r1 6 fresh introduced P1; r2 those 6 resolved via the aggregate record + 1 fresh P1) reaches a normal round-3 reservation with **no stall of any class**, with the `fixed` statuses produced by the production parser (not injected)
- [ ] Case 2: churn counter-case (same `chainRoot` `not_fixed` in both rounds) still ESCALATEs via the production reservation path
- [ ] Case 3: rounds with zero resolution evidence never stall early and are bounded only by the cap
- [ ] Case 4 (R8): one explicit `not-fixed` in round 2 followed by a round 3 that omits it does **not** stall, via the production reservation path
- [ ] `docs/review-findings.md` states the literal grammar, the aggregate record, and the `unaddressed: []` non-signal note
- [ ] `docs/README.md` "Notable updates" bullet added; `docs/troubleshooting.md` root-cause list updated; no stall-class name survives anywhere in docs
- [ ] `knowledge/decisions/` entry written with all 7 required elements in order, including the verbatim docstring quote, the churn-is-real caveat, and the explicit fn-159 R2 supersession
- [ ] CHANGELOG `## Unreleased` entry, outcome-first; **no version bump**
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`
- [ ] Propagation verified: `.flow/bin/flowctl.py` current, `./scripts/sync-codex.sh` run twice with no second-run diff, `test_prompt_text_pinned` green

## Done summary
Proved the whole seam on the production reservation path, then landed docs, the decision record, the CHANGELOG entry, and the full gate.

**Four e2e cases**, each driving reserve → `record_review_attempt` → findings attach for every round, so the digests the stall rule reads are built by the real parser from real reviewer text (`.3`'s direct-digest tests prove the classifier; these prove the seam end to end):
1. **The fn-158 field pair** — round 1 raises 6 freshly introduced P1s; round 2 resolves them with the aggregate all-clear the prompt now states and raises one more P1 → a normal round-3 reservation, **no stall of any class**. Asserts the intermediate digest too (6 `fixed` + 1 `open`, exactly one `firstSeenThisRound`).
2. **Churn counter-case** — the same finding explicitly `not-fixed` in two consecutive rounds still ESCALATEs on `same-not-fixed-lineage`.
3. **No-grammar case** — a reviewer that never uses the grammar runs **every** round the cap allows without an early stall, and the next reservation is asserted to exit `REVIEW_CAP_EXIT_CODE` with the `MAX_REVIEW_ITERATIONS=<cap>` message and **not** a stall marker. (Strengthened on impl-review round 1: it originally stopped at "still reservable", which did not actually prove the loop ends on the cap — my commit message had overclaimed that.)
4. **R8 asymmetric case** — one `not-fixed` in round 2, then a round that raises something new while omitting the prior → carried status resets to `open`, round 4 reserves normally.

**Docs.** `review-findings.md` gains a "prior-finding reply grammar" subsection under Identity and lineage: the literal per-ordinal lines, the accepted statuses and aliases, the single-item shorthand, the aggregate record with its whole-line requirement and explicit-beats-implicit rule, the `unaddressed: []` non-signal, the unrepeated-`not_fixed` reset, and the fact that prose resolutions are invisible to the parser. `docs/README.md` gains a Notable-updates bullet. `docs/troubleshooting.md` gains the missing-grammar root cause plus a new note that **running to the cap is now the expected shape for a non-compliant reviewer, not a bug**, with the "lower the cap, do not re-add trend inference" instruction. `docs/flowctl.md` (~:2000) was already rewritten by `.3`.

**Decision record** — `knowledge/decisions/review-stall-detection-reads-resolution-2026-08-05.md`, all seven required elements in order: the failure-direction flip as a table; `get_max_review_iterations()`'s docstring quoted verbatim as the historical hinge, closing on *"the answer was better evidence, not better inference"*; both observed `unaddressed` transcript tails (round 1 with priors that did not exist, round 3 SHIP with no discussion of priors); the 3-false-positives-vs-0-true-positives record with the full causal chain, plus the **required caveat** that churn is real in the PR channel bounded by `land.ciFixBudget` and that deleting the rules is not deciding churn is a myth; the same-defect-class argument; accepted consequences (a)–(e); and the explicit **fn-159 R2 supersession**. It closes with a triage list for the predictable future reader who finds a runaway loop and wants to reinvent a trend rule.

**CHANGELOG** `## Unreleased`, outcome-first. Added the mandatory unheaded user-outcome paragraph on impl-review round 1 — `agent_docs/releasing.md` requires it for any release whose value spans more than one bullet, and this one spans five across Fixed/Changed/Added. No version bump (batched).

**One unplanned artifact update, worth flagging:** the required host-workflow grammar grew the plan-review `host` route from 17069 to 18017 chars, so fn-130's tracked reduction for that single route drops 64.8% → 62.8% in `optimization/reached-path/runs/plan-review-candidate.json`. Recomputed from the live measurement rather than left stale; the other five routes are unchanged. `test_backend_spec` pins tracked-vs-live equality, which is what surfaced it.

**Full gate:** `python3 scripts/run_tests_parallel.py` → 182 files, **4219 tests, 0 failures, 0 errors**, 5 skipped. `uvx ruff@0.16.0 check .` clean. `test_prompt_text_pinned` green with no hash change (the ratchet strings are function-local, so nothing pinned them — R6 is the drift guard instead). Propagation verified: `.flow/bin/flowctl.py` byte-identical, tracker manifest regenerated, `sync-codex.sh` run twice with no second-run diff. `grep -rn "flat-trajectory\|fresh-introduced-critical"` returns nothing across `flowctl.py`, `.flow/bin/`, live tests, and docs.
## Evidence
- Commits: c5025123, 064a5e10
- Tests: python3 scripts/run_tests_parallel.py  (182 files, 4219 tests, 0 failures, 0 errors, 5 skipped), uvx ruff@0.16.0 check .  (All checks passed), grep -rn 'flat-trajectory|fresh-introduced-critical' scripts/ .flow/bin/flowctl.py tests/ docs/  (no hits), cmp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py  (identical), ./scripts/sync-codex.sh twice  (no second-run diff), flowctl codex impl-review fn-168-review-convergence-lost-ratchet-prompt.4  (r1 NEEDS_WORK 1xP1 cap terminal unasserted + 1xP2 changelog outcome paragraph; r2 VERDICT=SHIP, receipt /tmp/impl-review-fn-168-4.json, gpt-5.6-sol)
- PRs: