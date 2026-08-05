# Review convergence lost: ratchet prompt never states the prior-finding line grammar

## Goal & Context
<!-- scope: business -->

Three consecutive flow-swarm specs (fn-156, fn-157.2/fn-158.2 impl, fn-158 completion) hit `ESCALATE: review loop stalled (flat-trajectory)` on healthily converging loops — each round's findings were fully fixed and the open set was shrinking (6→1, 7→2), yet the counter refused the final round and the host had to hand-verify and record a basis in evidence.

Root cause, verified against live digests in flow-swarm's `.flow/specs/fn-158-…json` `review_attempts`:

- The digest carries prior findings forward as `status: open, firstSeenThisRound: false` unless the reviewer emits explicit per-ordinal resolution lines. `_review_finding_prior_items` parses those via `_FINDINGS_PRIOR_RECORD_RE` / `_FINDINGS_PRIOR_RE`, which require line-start records shaped `Prior finding #N: fixed|not-fixed|withdrawn` (aliases in `_FINDINGS_STATUS_ALIASES`). The carry-forward comment is explicit: "an omitted prior finding remains current until the reviewer explicitly fixes or withdraws it."
- The re-review ratchet prompt (`build_convergence_ratchet_block`) instructs: "For EACH prior finding above, state whether it is now **fixed** or **not-fixed**" — but never states the machine line grammar. Codex complies semantically (prose "All prior findings fixed", requirements tables, `unaddressed: []` in the JSON tail) and emits ZERO parseable records.
- Result: every carried finding stays `open` in the next round's digest; any round raising ≥1 new finding then has `current_open ≥ previous_open` with unimproved worst severity → `_review_stall_rule` returns `flat-trajectory` → ESCALATE at 2/8 rounds, exactly when the loop is one round from SHIP.

Observed digest (fn-158 completion r2): six carried P1s `open/firstSeen:false` + one new P1 = 7 open vs r1's 6 open. The reviewer's own text resolved all six.

This is the fn-136 memory class exactly (`bug/runtime-errors/structured-review-parsers-must-2026-07-30`): "separate presence detection from canonical parsing; recognized-but-invalid input must select invalid sentinel, never absent sentinel." Here the prompt under-specifies a machine format and the parser's conservative default silently degrades a healthy loop into a false stall.

## Architecture & Data Models
<!-- scope: technical -->

Fix both sides of the seam; either side alone closes the live failure, both make it robust:

1. **Prompt states the grammar (primary).** The shrink-only contract's rule 1 gains the exact machine format with an example block: one line per prior finding, line-start, `Prior finding #N: fixed` / `not-fixed` / `withdrawn`, using **the literal number rendered before each item** (ordinals are a stored per-item field, not a positional index — see below); prose/tables remain welcome but the lines are mandatory. One builder serves codex/copilot/cursor across impl/plan/completion (5 call sites, one function). **Host is a separate third surface** and needs the same wording by hand.
2. **Parser accepts a dedicated aggregate all-clear (fallback).** See the R2 amendment below — the originally-specified `unaddressed: []` trigger is unsound and is replaced.
3. **Classifier honesty guard (belt-and-braces).** A digest whose only `open` items are carried-and-unverified must not satisfy `flat-trajectory` on its own — the classifier requires at least one re-affirmed (`not_fixed`) or fresh open finding in the current round before declaring a stall. `same-not-fixed-lineage` and `fresh-introduced-critical` semantics unchanged.

### Plan-time verifications (2026-08-05; re-grep every line ref — the file drifts)

- **Ordinals are safe.** `ordinal` is a stored per-item field assigned at creation (`next_ordinal`, ~`flowctl.py:5601-5621`) with uniqueness enforced in container validation (~`:5404`); carried items keep it through the deep-copy. It is NOT a positional render index, so `Prior finding #2` cannot re-bind to a different finding when the prior set shrinks. The grammar example must still tell the reviewer to echo the rendered number rather than invent a 1..N scheme.
- **R3 needs no schema change — the non-goal holds.** `status: "open"` is written ONLY at initial creation (~`:4920`, `:5540`); carry-forward deep-copies without resetting, and only matched ordinals get an explicit status. Therefore `status == "open" && firstSeenThisRound == false` is unambiguously "carried and never touched by any ratchet line, any round", while an explicitly re-affirmed prior reads `not_fixed`. The classifier guard is a pure inference over the **existing** digest row — no `verifiedThisRound` field, digest shape unchanged.
- **Prompt text is NOT hash-pinned.** `build_convergence_ratchet_block`'s prefix/suffix are function-local strings; `test_prompt_text_pinned` discovers module-level constants + on-disk templates only. So no hash blocks this edit — and no guard exists against future drift either (see R6).
- **`REVIEW_JSON_TALLY_BLOCK` IS pinned** (~`:8893`) and already documents `"unaddressed"` as an R-ID array. Any textual change there needs a same-commit hash update with rationale.
- **MISMATCH → `None` is whole-container.** When `_FINDINGS_PRIOR_RECORD_RE` count != `_FINDINGS_PRIOR_RE` count (e.g. a stray `Prior finding #3: pending`), `_review_finding_prior_items` returns `None` and the call site (~`:5476`) drops the entire round's findings container — not just the bad line. Stating the grammar will produce MORE prior-finding lines, so this path gets more traffic: the aggregate detector must be ordered so a single malformed line cannot destroy an otherwise-clean round, and an out-of-vocabulary status must stay a recognized-but-invalid signal (never silently absent).
- **Fixture corpus is a 6-backend matrix.** `test_review_findings_fixture_corpus.py` drives `optimization/reached-path/fixtures/review-findings/v1/<backend>/<case>.md` from `INDEX.json`; a new case must land in `CASES` **and** `INDEX.json` for all six backends (codex, copilot, cursor, host, rp, export) or the matrix test hard-fails.

### R2 amendment — the specified `unaddressed: []` trigger is unsound

`unaddressed` answers "which spec R-IDs did this review leave uncovered"; a prior *finding* is not an R-ID. A reviewer can legitimately emit `unaddressed: []` (every R-ID covered) while a structured prior finding is genuinely still `not_fixed` — e.g. a P2 code-quality finding attached to no R-ID. Marking all carried priors `fixed` off that signal would stamp real open findings as resolved, drop them from the classifier's open set, and corrupt `same-not-fixed-lineage` — a worse failure than the one being fixed, and invisible.

**Replacement:** a **dedicated aggregate record in the same line-start family** — `Prior findings: all fixed` — stated in the prompt beside the per-ordinal grammar and parsed by the same machinery. It is explicit, purpose-built, cannot be produced by an R-ID-coverage judgment, and keeps "explicit beats implicit" (any per-ordinal record disables it). Scope: fires only when the prior set is non-empty, and sweeps only items currently `open`/`not_fixed` — **never** `withdrawn` (already resolved differently; re-stamping it `fixed` would corrupt lineage).

Accepted consequence: a reviewer that ignores the prompt entirely emits neither the per-ordinal lines nor the aggregate record, so part 2 does not rescue it — **part 3 does** (the loop survives; the container just carries honest unverified priors). That is the correct division: part 2 improves container honesty for compliant reviewers, part 3 guarantees the loop never falsely stalls regardless of reviewer compliance. `unaddressed: []` is explicitly documented as NOT vouching for prior findings.

## Edge Cases & Constraints

- **Withdrawn is never swept** by the aggregate path (it is a resolved-differently terminal, not an open item).
- **Aggregate ordering vs the `None` path**: evaluate the aggregate record and the per-ordinal records in one pass over the same line family so a malformed stray line is a recognized-but-invalid signal, not a silent absence, and cannot erase a clean aggregate round. Round-1 (no prior set) never activates the aggregate path.
- **Single-item prior sets**: `_review_finding_prior_items` special-cases one prior item with no ordinal (~`:5171`) — the grammar example must not imply ordinals are mandatory in that shape.
- **Host backend never sees the prompt.** The 3 `workflow-host.md` files state the prior-findings contract in prose with no reply grammar, so host rounds carry priors at `open` forever. fn-168 fixes the wording in all three; whether the host reviewer's *compliance* deserves its own enforcement is an Open Question, not scope creep here.
- **Mirror + propagation**: editing `workflow-host.md` requires `./scripts/sync-codex.sh` twice (idempotent, second run must show no diff); the 3 canonical files + 3 mirrored copies land in one change.
- **No behavior change for round-1 reviews or legacy receipts** (no findings container, or a container from before this change) — regression-tested.
- **Test production paths, not parallel constructions** (memory `test-production-path-not-parallel-construction-2026-05-21`): fixture tests must drive the real `_review_finding_prior_items` / digest / `_review_stall_rule`, never hand-built dicts mirroring the expected shape.
- **fn-166 ordering**: fn-166 (flowctl module split) plans to extract this exact region (`get_max_review_iterations` … `build_convergence_ratchet_block`, incl. `_review_stall_rule`) into `flowctl_review/`. fn-168 lands FIRST — it is a small behavior fix, fn-166 has 0 tasks started, and fn-166's extraction is symbol-bounded and explicitly zero-behavior-change, so it picks up the fixed code verbatim.

## Quick commands
```bash
# Focused suites (per-task baseline + verify)
cd plugins/flow-next/tests && python3 -m unittest test_review_findings_parser test_review_findings_receipts test_review_findings_fixture_corpus -q
cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_review_json_tallies test_prompt_text_pinned -q
```

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The ratchet/shrink-only prompt block states the exact per-ordinal line grammar with an example (line-start `Prior finding #N: fixed|not-fixed|withdrawn`, echoing the rendered ordinal), and a fixture-driven test proves a codex-style compliant response yields carried items with correct `fixed`/`not_fixed` statuses in the receipt findings container via the production parser. The same wording lands in all 3 `workflow-host.md` files. Errors: an out-of-vocabulary status word (e.g. `pending`) stays a recognized-but-invalid signal (existing whole-container `None`), never a silent absence; a single-item prior set without an ordinal still parses.
- **R2 (amended at plan time — see the R2 amendment above):** A dedicated aggregate all-clear record `Prior findings: all fixed`, stated in the prompt and parsed in the same line-start family, marks every carried prior currently `open`/`not_fixed` as `fixed`. Any per-ordinal record disables the aggregate path (explicit beats implicit); `withdrawn` items are never swept; the path never fires on an empty prior set. `unaddressed: []` alone is explicitly NOT a prior-findings signal (documented, and negative-tested). Absent both signals, today's conservative carry-forward stands. Table-tested. Errors: aggregate record + a contradicting per-ordinal `not-fixed` → the explicit line wins; malformed stray line + aggregate record → recognized-but-invalid, never a silent all-clear.
- **R3:** Classifier guard: a digest pair where the current round's open set consists solely of carried-unverified priors (`status == "open"` with `firstSeenThisRound == false`) plus new findings, with the new-finding count strictly below the prior round's open count, does NOT classify `flat-trajectory`. The fn-158 completion shape (6 open → 6 carried-unverified + 1 new) is the named regression fixture and must pass through to a normal round-3 reservation. Genuine stalls still classify: a re-affirmed `not_fixed` overlap, and equal-or-growing fresh open sets. Implemented as an inference over the existing digest row — no new digest/receipt field. Errors: a digest pair failing validation keeps today's behavior; `same-not-fixed-lineage` / `fresh-introduced-critical` unchanged.
- **R4:** End-to-end: a scripted two-round codex-style transcript (round 1 NEEDS_WORK with findings; round 2 NEEDS_WORK resolving all priors via the stated grammar + one new finding) reaches round 3 without ESCALATE under the default caps, driving the production reservation path. A second scripted transcript that genuinely stalls still ESCALATEs. No error surface beyond the assertions.
- **R5:** Docs: the 3 review-backend host workflow files plus `docs/review-findings.md` state the line grammar and the aggregate record (and that `unaddressed: []` is not a prior-findings signal); `docs/README.md` "Notable updates" gains a bullet (precedent: the 3.14.0 convergence bullet); CHANGELOG `## Unreleased` entry, outcome-first; codex mirror regenerated (`sync-codex.sh` twice, no second-run diff). No version bump (batched). No error surface beyond the final gate.
- **R6:** The ratchet prompt gains a regression guard against silent drift: a test asserts the emitted block contains the grammar AND that the example line itself matches `_FINDINGS_PRIOR_RECORD_RE` / `_FINDINGS_PRIOR_RE` (prompt and parser can never diverge unnoticed). Errors: no error surface — a pure assertion.

## Boundaries
<!-- scope: business -->

- No change to the review cap, reservation/refund machinery, or the other stall classes' semantics.
- No new receipt schema fields and no digest-shape change (verified achievable — see plan-time verifications).
- No relaxation for genuinely flat loops: a reviewer that re-affirms the same finding (`Prior finding #N: not-fixed`) twice still stalls exactly as today.
- Not a rewrite of the findings container, lineage model, or fixture-corpus format.
- Not host-reviewer *compliance enforcement* — fn-168 fixes host wording only (see Open Questions).

## Strategy Alignment

Active tracks served:
- **Ralph autonomous mode** — convergence-aware review terminals are a named pillar of the autonomy track ("multi-model review at every handover, convergence-aware review terminals … don't-thrash reflexes"). A false `flat-trajectory` at round 2 is precisely the thrash-reflex misfiring against a healthy loop, and it forced human hand-verification three specs in a row — the loop-quality invariant the track claims.
- **Self-improving through normal work** — the fix is graduated directly from field evidence (live digests + three escalations) and from an existing memory entry describing this exact parser class.

## Decision Context

Why fix both sides: the prompt fix alone leaves every non-compliant reviewer able to re-trigger the false stall; the classifier guard alone leaves the container accumulating phantom open priors that corrupt lineage over long loops. Together, compliance improves honesty and the guard makes the loop robust regardless.

Why the amended aggregate signal rather than the spec's `unaddressed: []`: that key answers R-ID coverage, not finding resolution, so a legitimately-`[]` response can coexist with a genuinely unfixed finding — the original R2 would have converted a false stall into a false SHIP, which is strictly worse (invisible instead of loud). A dedicated line-family record is unambiguous by construction and costs one prompt sentence. Recorded because it contradicts the spec as authored.

Why no new digest field for R3: the status lifecycle already encodes the distinction (`open` is only ever written at creation; explicit resolution writes `fixed`/`not_fixed`/`withdrawn`), so carried-unverified is reconstructible from the existing row — honoring the non-goal without weakening the guard.

Why fn-168 before fn-166: fn-166 moves this code wholesale with zero behavior change and has not started; landing a small fix first costs fn-166 a rebase, whereas the reverse entangles a behavior fix with a large mechanical extraction mid-flight.

## Early proof point
Task fn-168-review-convergence-lost-ratchet-prompt.3 validates the core claim (the fn-158 digest shape stops classifying `flat-trajectory` while genuine stalls still do) — it is the only task that proves the escalations actually stop, and it depends on nothing. If the carried-unverified inference turns out not to separate those two cases cleanly, the no-new-field non-goal must be reopened before the prompt/parser work is worth landing.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Prompt grammar + example, host wording, compliant-response fixture test | .1 (prompt/docs), .2 (parser fixture test) | — |
| R2 | Dedicated aggregate all-clear record, scoped + explicit-wins, table-tested | .2 | — |
| R3 | Classifier guard + fn-158 regression fixture + genuine-stall tests | .3 | — |
| R4 | Two-round end-to-end transcript reaches round 3 | .4 | — |
| R5 | Docs + Notable updates + CHANGELOG + mirror regen | .4 | — |
| R6 | Prompt/parser drift guard (example matches the regexes) | .1 | — |

## References

- `plugins/flow-next/scripts/flowctl.py` — `build_convergence_ratchet_block` (~:11807-11911, rule 1 ~:11861), `build_rereview_preamble` (~:11914), `_review_finding_prior_items` (~:5134-5207, call site ~:5476), `_FINDINGS_PRIOR_RE` / `_FINDINGS_PRIOR_RECORD_RE` / `_FINDINGS_STATUS_ALIASES` (~:4577-4648), `_review_stall_rule` (~:11187-11284, flat-trajectory ~:11251-11270), `build_review_findings_digest` (~:5954-5984), `_findings_digest_chain_roots` (~:5888), journal recovery rows (~:9854, :9870), `extract_review_json_block` / `_review_json_block_schema_ok` / `_unaddressed_from_json` (~:6626-6731), `REVIEW_JSON_TALLY_BLOCK` (~:8893, PINNED)
- Ratchet call sites (5, one builder): ~:39542, :40413, :40900, :41165, :41215
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md` (~113-118), `flow-next-plan-review/workflow-host.md` (~83-84), `flow-next-spec-completion-review/workflow-host.md` (~130-133)
- Tests: `test_review_findings_parser.py` (grammar accept/reject ~:368-437), `test_review_convergence_cap.py` (`TestConvergenceRatchet` ~:86), `test_review_findings_fixture_corpus.py` (matrix ~:37), `test_review_findings_receipts.py`, `test_review_json_tallies.py`, `test_prompt_text_pinned.py` (`PROMPT_HASHES` ~:89)
- Fixtures: `optimization/reached-path/fixtures/review-findings/v1/<backend>/<case>.md` + `INDEX.json` (6 backends)
- Docs: `plugins/flow-next/docs/review-findings.md` (~100-121), `docs/README.md` "Notable updates" (~54-70), `docs/troubleshooting.md` (~83), `docs/flowctl.md` (~2026)
- Memory: `bug/runtime-errors/structured-review-parsers-must-2026-07-30` (this exact class), `bug/build-errors/fn-44-review-cycle-lessons-2026-05-21`, `bug/test-failures/test-production-path-not-parallel-construction-2026-05-21`, `knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30`, `knowledge/workflow/pr-bot-review-loops-do-not-converge-2026-08-04`
- Coordination: fn-166 (extraction of this region — land fn-168 first), fn-158 (unrelated line anchor at ~:11376 churns)

## Open Questions

- **Host-reviewer compliance (surfaced by gap analysis; not blocking).** Host rounds never pass through the ratchet builder, so even after the wording fix a host reviewer that ignores the grammar keeps priors at `open` forever — and R3's guard then exempts host reviews from ever stalling on genuinely stuck priors. fn-168 fixes the wording in all 3 files; whether host needs its own enforcement (structured reply contract, or a rounds-carried ceiling) is a follow-up spec if it shows up in the field.
- Should the ratchet prefix/suffix be promoted to module-level pinned constants (bringing them under `test_prompt_text_pinned`) rather than covered by R6's targeted assertion? R6 is the cheaper guard; promotion is a larger, hash-churning change. Decided in task .1 if it turns out to be a one-liner.
