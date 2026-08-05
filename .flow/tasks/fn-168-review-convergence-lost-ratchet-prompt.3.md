---
satisfies: [R3]
---
# fn-168-review-convergence-lost-ratchet-prompt.3 Delete both inference stall classes (flat-trajectory, fresh-introduced-critical)

## Description
Delete both inference-based stall classes — `flat-trajectory` and `fresh-introduced-critical` — leaving `same-not-fixed-lineage` and the deterministic cap as the only terminals. This is the spec's **early proof point**: it depends on nothing and proves the escalations actually stop.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`_review_stall_rule`), `plugins/flow-next/tests/test_review_convergence_cap.py`, `plugins/flow-next/docs/flowctl.md`, `.flow/bin/flowctl.py` (propagation)

### Approach
- **Delete the `flat-trajectory` branch** in `_review_stall_rule` (~:11187): the `previous_open`/`current_open` severity+count comparison, **including the evidence-filtering fix already committed as `9417ba9b`** and its `evidence_bearing_open()` helper (~:11253). With the class gone the helper is unreachable dead code — revert/supersede it as part of the deletion, do not leave it orphaned. Check whether `open_statuses` (~:11251) still has a live consumer after both deletions; remove it too if not.
- **Delete the `fresh-introduced-critical` branch**: the `has_fresh_critical()` double-`any()` test (~:11290-11301). Two independent `any()` calls with no cross-round linkage and no resolution check — "two consecutive rounds each found a new P1" fires on every healthy thorough loop (field: fn-156 / fn-157 / fn-158 — different P1s each round, all fixed, converged to merge).
- **Keep `same-not-fixed-lineage` exactly as it is**, including its `same_identity` gate (backend + reviewKind must match). It is the one rule grounded in an explicit reviewer statement: `not_fixed` is written only by a parsed per-ordinal resolution line, never at creation (`open` at ~:4920, :5540, :5123). Keep the cap, reservation/refund, transport-health, and `NEEDS_HUMAN` paths untouched.
  - **Do NOT weaken or re-gate this rule here.** Carry-forward *does* propagate an unrepeated `not_fixed`, which would let the rule fire on a pair of rounds where only one carried a statement — but that hole is closed on the **parser** side by R8 in `.2` (carried `not_fixed` resets to `open`), not by touching `_review_stall_rule`. This task's contract is deletion only.
  - Consequently, this task's churn test constructs digest rows where **both** rounds hold `not_fixed` — the shape the parser will only produce when the reviewer stated `not-fixed` twice. That is legitimate: direct-digest tests exercise the classifier, and the parser-side proof lives in `.2`/`.4`.
- **Delete the stall assertions referencing the doomed classes** in `test_review_convergence_cap.py` (11 tests reference stall classes; the dedicated ones sit at ~:4304 and ~:4341). `test_other_stall_classes_ignore_the_evidence_bearing_filter` **SPLITS**: its lineage half survives, its `fresh-introduced-critical` half goes. Grep the whole test file — do not assume the count.
- **Rewrite** `plugins/flow-next/docs/flowctl.md` (~:2000, which explains the identity-vs-aggregate stall split) rather than deleting the sentence: after this change there is no aggregate class, so the doc must say the cap is the aggregate bound.
- **Early proof point (this is why the task is first, not last).** `.3`'s tests write digest rows DIRECTLY (`self._digest(self._carried(...))`), so it can assert the fn-158 shape — round 1: 6 fresh introduced P1; round 2: those 6 carried at `fixed` + 1 fresh P1 — classifies **no stall of any class**, WITHOUT `.1`/`.2` having landed. Also assert the churn counter-case still classifies: the same `chainRoot` at `not_fixed` in both rounds → `same-not-fixed-lineage`.
- Sanity-check the surviving fail-inert paths keep today's behavior: digest-pair validation failure, truncated digests, epoch boundaries, and backend/kind switches.
- Propagation: `cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py`.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py` — `_review_stall_rule` (~:11187-11302) in full: the consumed-row filter, digest validation, `same_identity`, and the three class branches
- `plugins/flow-next/scripts/flowctl.py` — `_review_stall_marker` (~:11307) and the stall consult inside `_enforce_and_increment_review_cap_locked` (~:11598): confirm nothing else enumerates the class names
- `plugins/flow-next/tests/test_review_convergence_cap.py` — every stall-class reference (~:4295-4472 plus any elsewhere in the file); decide keep / delete / split per test
- `plugins/flow-next/docs/flowctl.md` (~:2000) — the identity-vs-aggregate sentence to rewrite

**Optional** (reference as needed):
- `git show 9417ba9b` — the guard being reverted, so the revert is complete rather than partial
- `plugins/flow-next/scripts/flowctl.py` — `build_review_findings_digest` (~:5954-5984) for the digest row shape the tests construct

### Key context
- **Accepted consequences — do not "fix" these later, they are the decision** (spec Boundaries (a)-(d)): non-repeating churn loses early detection and is cap-bounded; backend switches lose all early detection (`same_identity` gate); host is cap-only in practice. The predictable failure mode is someone seeing a runaway loop in six months and reinventing `flat-trajectory` — `.4`'s decision entry is the vaccine, and this task's code comments should point at it.
- Empirical record: 3 recorded false positives (fn-156/157/158) vs **0 recorded true positives** for either deleted class.
- Leave a short comment at the surviving class explaining WHY it survived (it reads an explicit statement; the deleted classes read derived aggregates), so the next reader does not "restore symmetry".
- `MAX_REVIEW_ITERATIONS` (default 8) is untouched here; the config valve is `.5`.

## Acceptance
- [ ] `_review_stall_rule` contains exactly ONE stall class: `same-not-fixed-lineage`, with its `same_identity` gate intact
- [ ] `flat-trajectory`, `evidence_bearing_open()`, and `fresh-introduced-critical` / `has_fresh_critical()` are gone; `9417ba9b`'s guard fully reverted with no orphaned helpers or dead locals
- [ ] `grep -rn "flat-trajectory\|fresh-introduced-critical"` returns no hits in `flowctl.py`, `.flow/bin/flowctl.py`, live tests, or `plugins/flow-next/docs/flowctl.md`
- [ ] Early proof point, via direct digest rows and no dependency on `.1`/`.2`: the fn-158 shape (6 fresh introduced P1 → 6 carried `fixed` + 1 fresh P1) classifies **no stall of any class**
- [ ] Churn counter-case still classifies: same `chainRoot` at `not_fixed` in two consecutive digests → `same-not-fixed-lineage`
- [ ] `_review_stall_rule` is NOT otherwise modified — the unrepeated-`not_fixed` hole is closed parser-side by R8 in `.2`, not here
- [ ] Fail-inert paths unchanged: digest-pair validation failure, truncated digests, epoch boundaries, backend/kind switches
- [ ] Cap, reservation/refund, transport-health, and `NEEDS_HUMAN` terminals untouched
- [ ] Deleted/split test assertions accounted for by grep, not by assumption; `docs/flowctl.md` ~:2000 rewritten, not deleted
- [ ] A comment at the surviving class states why it survived (explicit statement vs derived aggregate)
- [ ] Focused suites green: `python3 -m unittest test_review_convergence_cap test_review_findings_receipts test_review_findings_parser -q`
- [ ] Propagation done (cp flowctl.py to .flow/bin)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
