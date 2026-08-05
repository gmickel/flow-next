# Review convergence lost: ratchet prompt never states the prior-finding line grammar

> **Shape note (re-planned 2026-08-05):** the title names the entry point; the fix is broader. Stall
> detection stops *inferring* convergence and starts *reading* it — the grammar lands, and both
> heuristic stall classes are deleted. The spec id/slug is unchanged deliberately (branch, FLOW-95,
> and every task id key off it).

## Goal & Context
<!-- scope: business -->

Three consecutive flow-swarm specs (fn-156, fn-157.2/fn-158.2 impl, fn-158 completion) hit `ESCALATE: review loop stalled (flat-trajectory)` at round **2 of 8** on healthily converging loops — each round's findings were fully fixed and the open set was shrinking (6→1, 7→2) — and a human had to hand-verify and record a basis in evidence each time.

Root cause, verified against live digests in flow-swarm's `.flow/specs/fn-158-diff-comments-queue-anchored-follow-ups.json` → `review_attempts`:

1. On a re-review, `build_convergence_ratchet_block` renders the prior findings and instructs: *"For EACH prior finding above, state whether it is now **fixed** or **not-fixed**"* — but **never states the machine line grammar** the parser requires (line-start `Prior finding #N: <status>`).
2. Codex complies **semantically**: prose "All prior findings fixed", a requirements table, and `"unaddressed": []` in the JSON tail. It emits **zero parseable records**.
3. `_review_finding_prior_items` therefore updates no statuses. Its documented default — *"an omitted prior finding remains current until the reviewer explicitly fixes or withdraws it"* — carries every prior forward at `status: "open"`, `firstSeenThisRound: false`.
4. The round's digest shows an **inflated open set**: fn-158 completion r2 = 6 carried P1s + 1 genuinely new P1 = **7 open**, against r1's **6 open**.
5. `flat-trajectory` compares the two rounds: open count did not strictly decrease (7 ≥ 6) and worst severity did not strictly improve (P1 → P1) → **stall** → exit 4 at round 2, one round from SHIP.

**A first implementation attempt then surfaced the deeper defect (why this spec was re-planned).** Filtering `flat-trajectory` to evidence-bearing opens does NOT stop the escalations: the same digests then classify **`fresh-introduced-critical`**, because r1 had a fresh introduced P1 and r2 had a fresh introduced P1 — and that rule reads only fresh items, so no amount of evidence-filtering touches it. Two consecutive rounds each finding a new P1 is what *every healthy thorough loop* looks like (fn-156/157/158 in the field: different P1s each round, all fixed, converged to merge), and the rule never checks whether anything was resolved. **The label changes; the escalation does not.**

Both classes are therefore the same defect: **round-local snapshots inferring convergence from evidence the parser never reliably captured.** The fix is not a better inference. It is to make resolution *explicit* and delete the inferences.

This is exactly the class the memory entry `bug/runtime-errors/structured-review-parsers-must-2026-07-30` warns about: *"separate presence detection from canonical parsing; recognized-but-invalid input must select invalid sentinel, never absent sentinel."*

## Architecture & Data Models
<!-- scope: technical -->

Stall detection stops **inferring** convergence and starts **reading** it.

**Add explicit resolution evidence:**
1. **The prompt states the grammar.** The shrink-only contract's rule 1 gains the exact machine format with an example: line-start `Prior finding #N: fixed` / `not-fixed` / `withdrawn`, echoing **the literal rendered ordinal**. Same wording by hand into all 3 `workflow-host.md` files (host never passes through the builder).
2. **A dedicated aggregate record** — `Prior findings: all fixed` — in the same line-start family, for the common "I fixed everything" round.
3. **Every token the prompt advertises must be in the parser's vocabulary** (this is a live bug today, not something the spec introduces — see below).

**Delete both inference-based stall classes** from `_review_stall_rule`:
- **`flat-trajectory`** — the `previous_open`/`current_open` severity+count comparison, deleted entirely, **including the evidence-filtering fix already committed as `9417ba9b`** and its `evidence_bearing_open()` helper (unreachable dead code once the class is gone).
- **`fresh-introduced-critical`** — the `has_fresh_critical()` double-`any()` test, deleted entirely. Two independent `any()` calls with no cross-round linkage and no resolution check.

**Keep exactly two terminals:**
- **The hard round cap** — `MAX_REVIEW_ITERATIONS` (default 8), flowctl-owned reservation/refund, unchanged. The safety gate and cost ceiling.
- **`same-not-fixed-lineage`** — now the ONLY stall class. It reads `previous_not_fixed & current_not_fixed` over `chainRoot` where `status == "not_fixed"`, retaining its `same_identity` gate (backend + reviewKind must match). `not_fixed` is written only by an explicit parsed reviewer resolution line — never at creation (`open` is written at ~`flowctl.py:4920`, `:5540`, `:5123`). So lineage reads a *statement*; the deleted rules read *derived aggregates*.

**But that statement must be made every round it counts (plan-review round 1, P0).** Verified in `_review_finding_prior_items`: carry-forward deep-copies `status` **verbatim** and overwrites it only for ordinals parsed *this* round. So a prior explicitly marked `not-fixed` in round 2 and then merely omitted in round 3 sits at `not_fixed` in **both** digests, the lineage intersection is non-empty, and the loop escalates — even though round 3 said nothing, or fixed it and replied in prose. That is the original false-stall failure mode surviving inside the survivor, and it makes the "lineage reads a statement" claim true only for the round the statement was made.

**So carried statuses are reset before each round's records are applied (R8):** a carried item at `not_fixed` reverts to `open` (unverified); `fixed` and `withdrawn` are preserved (they are resolved terminals, and re-opening them would corrupt lineage). `same-not-fixed-lineage` then requires an explicit `not-fixed` statement in **both** consecutive rounds — which is exactly what "the reviewer says twice that this is still broken" means. Accepted cost: the ratchet prompt renders such an item as `open` rather than `not_fixed`, losing the "you called this unfixed last round" nuance in the rendered status column. That is a prompt-copy concern, not an evidence concern, and it is the cheaper side of the trade than a new per-round-verification digest field (which the Boundaries forbid).

**Plus the missing valve:** `review.maxIterations` as a config key, because "lower the cap instead of re-adding inference" (see Decision Context) must be reachable. `get_max_review_iterations()` (~`:9556`) is **env-only** today with no config key and none in the published schema, so the advertised knob would otherwise mean threading an env var through pilot, land, ralph, and every manual invocation with nothing persisted.

**The valve must not become a self-grant path — and the existing one already is (plan-review round 1, P0).** Verified against `ralph-guard.py`: `config set` is not on the recovery blocklist, `.flow/config.json` is **not** in `PROTECTED_FILE_PATTERNS` (which holds `ralph-guard.py`, `flowctl.py`, `.claude/settings.json`, …), and nothing screens a `MAX_REVIEW_ITERATIONS=99` assignment on a command — which is the **higher-precedence** path. So blocking only `flowctl config set review.maxIterations` would leave two open routes for an autonomous agent to extend its own gate, one of them pre-existing. R7 therefore closes all three: the `config set` verb (tokenized), the config file against file tools, and the env assignment.

Net diff **shrinks**.

### Why the trade is right

The failure direction flips for a non-compliant reviewer:

| priors stick at `open` | before | after |
|---|---|---|
| effect | inflated open set → **false stall at round 2** — a *correctness* failure, silent, forces hand-verification | lineage silent → **runs to the cap** — a *cost* failure, bounded and visible |

Non-compliance stops producing *wrong* answers and starts producing *expensive* ones: **correctness over cost, with the cap as the ceiling.** This also promotes **R6 to load-bearing** — the prompt/parser drift guard now protects the only terminal that can still fire.

### Plan-time verifications (2026-08-05; re-grep every line ref — the file drifts)

- **Symbol names.** The stall classifier is `_review_stall_rule` (~`:11187`); `_review_stall_marker` (~`:11307`) formats the terminal string. There is **no** `_review_stall_classification`.
- **The advertised grammar is NOT in the parser's vocabulary — verified live by running the compiled regexes:**

  | line | `_FINDINGS_PRIOR_RE` | `_FINDINGS_PRIOR_RECORD_RE` | result |
  |---|---|---|---|
  | `Prior finding #2: fixed` | 1 | 1 | ok |
  | `Prior finding #2: not fixed` | 1 | 1 | ok |
  | `Prior finding #2: not_fixed` | 1 | 1 | ok |
  | `Prior finding #2: not-fixed` | **0** | 1 | **MISMATCH → container `None`** |
  | `Prior findings: all fixed` | **0** | 1 | **MISMATCH → container `None`** |

  `_FINDINGS_PRIOR_RE` (~`:4625`) spells the negative status `not[\s_]fixed` — whitespace or underscore, **not a hyphen** — and `_FINDINGS_STATUS_ALIASES` (~`:4577`) has no `not-fixed` key. A RECORD/PRIOR count mismatch makes `_review_finding_prior_items` return `None`, and the call site (~`:5476`) drops **the whole round's findings container** — fail-inert, no error, no warning. **This is a live bug today:** the current prompt's own prose says *"state whether it is now **fixed** or **not-fixed**"* — it advertises the hyphen the parser rejects.
- **Ordinals are safe.** `ordinal` is a stored per-item field assigned at creation (`next_ordinal`, ~`:5601-5621`) with uniqueness enforced in container validation (~`:5404`); carried items keep it through the deep-copy. It is NOT a positional render index, so `Prior finding #2` cannot re-bind when the prior set shrinks. `_render_structured_prior_finding` (~`:11780`) emits each item as `{ordinal}. {severity} | {classification} | {status} | {title} | {location}`, so the grammar must tell the reviewer to echo that leading number.
- **Single-item prior sets** are special-cased with no ordinal (~`:5171`), so the grammar example must not imply ordinals are mandatory.
- **Prompt text is NOT hash-pinned.** `build_convergence_ratchet_block`'s prefix/suffix are function-local strings; `test_prompt_text_pinned` discovers module-level constants + on-disk templates only. So no hash blocks this edit — and no guard exists against future drift either (that is R6). **`REVIEW_JSON_TALLY_BLOCK` (~`:8893`) IS pinned** — do not touch it.
- **`get_max_review_iterations()` has 7 call sites** (~`:11337`, `:29676`, `:29844`, `:40664`, `:41113`, `:41458`, plus the def). Adding a config read must not add 7 config round-trips.
- **`flowctl config set` is NOT on the ralph-guard blocklist.** The screens (`plugins/flow-next/scripts/hooks/ralph-guard.py` ~`:702-738`, ~`:1200-1234`, argv pass ~`:1340-1370`) block `reset-review-rounds`, `review-rounds reset`, and `--force` dispatches. Nothing blocks `config set`.
- **`review` is a CLOSED object in the published schema** (`scripts/gen_flow_config_schema.py`, TABLE ~`:561-572`, descriptions ~`:58`) holding only `review.backend`. A new key needs the TABLE entry + description + regenerated artifact or `test_flow_config_schema_drift` fails.
- **Fixture corpus is a 6-backend matrix at REPO ROOT:** `optimization/reached-path/fixtures/review-findings/v1/<backend>/<case>.md` driven from `INDEX.json` — **not** under `plugins/flow-next/`. A new case must land in `CASES` **and** `INDEX.json` for all six backends (codex, copilot, cursor, host, rp, export) or the matrix test hard-fails.

### R2's aggregate signal is a dedicated record — never `unaddressed: []`

`unaddressed` is part of the canonical closing JSON tail emitted in **every** review, including round 1 and rounds that say nothing about priors — it is **ambient**, not a deliberate statement of prior-finding resolution. Observed in this workstream's own reviews:

- plan-review **round 1** tail: `{"classification_counts":{"introduced":3,…},"unaddressed":["R1","R3","R6"]}` — a round where no prior findings exist at all
- plan-review **round 3** tail: `{"unaddressed":[]}` — a SHIP with zero discussion of priors

It also answers the wrong question: "which spec R-IDs did this review leave uncovered". A prior *finding* is not an R-ID, so a reviewer can legitimately emit `unaddressed: []` (every R-ID covered) while a structured prior finding is genuinely `not_fixed` — e.g. a P2 code-quality finding attached to no R-ID.

Under this design that is fatal, not merely sloppy: `same-not-fixed-lineage` is the only terminal and it reads exclusively `not_fixed`. An ambient signal that sweeps priors to `fixed` would **silently erase the only evidence stall detection has left** → no class could ever fire → every pathological loop would run to the cap with no diagnostic. A dedicated line-family record is safe by construction: only an actual statement about priors can produce it.

## Edge Cases & Constraints

- **Aggregate scope rules (all required):** fires only when the prior set is non-empty; sweeps only items currently `open`/`not_fixed`; **never** `withdrawn` (a resolved-differently terminal — re-stamping it `fixed` would corrupt lineage); **any** explicit per-ordinal record disables it (explicit beats implicit, enforced by parse order, not just documented).
- **Aggregate ordering vs the `None` path:** evaluate the aggregate record and the per-ordinal records in ONE pass over the same line family, so a malformed stray line stays recognized-but-invalid (whole-container `None`) and can never read as a clean aggregate round.
- **Stating the grammar increases traffic on the mismatch path** — more prior-finding lines means more chances of a count mismatch, so the vocabulary work is a precondition, not a nice-to-have.
- **No behavior change for round-1 reviews or legacy receipts** (no findings container, or a pre-change container) — regression-tested.
- **Digest pairs that fail validation, truncated digests, epoch boundaries, and backend/kind switches** keep today's fail-inert behavior.
- **Carried-status reset (R8) is scoped to `not_fixed` only.** `fixed` and `withdrawn` are resolved terminals and are preserved through carry-forward; re-opening them would corrupt lineage and re-raise findings the reviewer already closed. Round 1 has no carried items, so the reset is a no-op there.
- **Three self-grant routes, not one.** An autonomous agent could extend its own gate via `flowctl config set` (in either the leaf or the parent-key JSON form), via a file-tool write to `.flow/config.json` (not currently protected), or via the higher-precedence `MAX_REVIEW_ITERATIONS=99` env assignment (not currently screened — a **pre-existing** hole). All are blocked in ralph-guard with the same **tokenized** matching the existing screens use (memory `shell-command-allowlist-gates-must-2026-06-05`: tokenize, never substring-match), because fn-159's invariant is *"the implementing agent can never reset or extend its own gate"* and a durable config key with any route left open would be a net regression.
- **The parent-key write is the same mutation as the leaf write.** `_set_config_locked` `json.loads`-coerces a `{`-leading string value and its nested walk replaces whole subtrees, so `config set review '{"maxIterations":99}'` sets the cap without ever naming `review.maxIterations`. Any screen must cover both forms.
- **`config set` is blocked for the cap specifically, not wholesale.** Other config writers (tracker resolve transactions, setup) legitimately run under Ralph; a blanket `config set` block would break them, and `config set review.backend …` must keep working.
- **The ralph guard does not fire on Cursor** (different hook events), degrading to prose-only — exactly as the existing reset block already does.
- **Mirror + propagation:** editing `workflow-host.md` requires `./scripts/sync-codex.sh` twice (second run must show no diff); editing `flowctl.py` requires `cp` to `.flow/bin/flowctl.py`.
- **Test production paths, not parallel constructions** (memory `test-production-path-not-parallel-construction-2026-05-21`): tests must drive the real `_review_finding_prior_items` / digest / `_review_stall_rule` / reservation path, never hand-built container dicts.
- **fn-166 ordering:** fn-166 (flowctl module split) plans to extract this exact region (`get_max_review_iterations` … `build_convergence_ratchet_block`, incl. `_review_stall_rule`) into `flowctl_review/`. fn-168 lands FIRST — small behavior fix, fn-166 has 0 tasks started, and fn-166's extraction is symbol-bounded and explicitly zero-behavior-change, so it picks up the fixed code verbatim.

## Quick commands
```bash
# Focused suites (per-task baseline + verify)
cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_review_findings_parser test_review_findings_receipts test_review_findings_fixture_corpus test_review_json_tallies test_prompt_text_pinned -q
# .5 additionally
cd plugins/flow-next/tests && python3 -m unittest test_flow_config_schema_drift test_tracker_distribution -q
```

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The ratchet/shrink-only prompt block states the exact per-ordinal line grammar with an example (line-start `Prior finding #N: fixed|not-fixed|withdrawn`, echoing the rendered ordinal), and **every status token the prompt advertises is accepted by `_FINDINGS_PRIOR_RE`, recognized by `_FINDINGS_PRIOR_RECORD_RE` without creating a count mismatch, and normalized by `_FINDINGS_STATUS_ALIASES`** — today's regex spells the negative `not[\s_]fixed` and rejects the hyphen, so hyphen support lands with the wording. A fixture-driven test proves a codex-style compliant response yields carried items with correct `fixed`/`not_fixed` statuses in the receipt findings container **via the production parser**. The same wording lands in all 3 `workflow-host.md` files, with the codex mirror regenerated. Errors: an out-of-vocabulary status word (e.g. `pending`) stays a recognized-but-invalid signal (existing whole-container `None`), never a silent absence; a single-item prior set without an ordinal still parses.
- **R2:** A dedicated aggregate all-clear record `Prior findings: all fixed`, stated in the prompt and parsed in the same line-start family, marks every carried prior currently `open`/`not_fixed` as `fixed`. It must be recognized **without** forcing a RECORD/PRIOR count mismatch (verified live: today it matches the record regex and fails the canonical one, which would drop the container). Any per-ordinal record disables the aggregate path; `withdrawn` items are never swept; the path never fires on an empty prior set. **`unaddressed: []` alone is explicitly NOT a prior-findings signal — documented and negative-tested.** Absent both signals, today's conservative carry-forward stands. Table-tested. Errors: aggregate record + a contradicting per-ordinal `not-fixed` → the explicit line wins; malformed stray line + aggregate record → recognized-but-invalid, never a silent all-clear.
- **R3:** `flat-trajectory` and `fresh-introduced-critical` are **REMOVED** from `_review_stall_rule`; `same-not-fixed-lineage` and the deterministic cap are the only terminals. `9417ba9b`'s evidence-filtering guard and its `evidence_bearing_open()` helper are reverted as dead code. The fn-158 digest shape (round 1: 6 fresh introduced P1 → round 2: those 6 carried `fixed` + 1 fresh P1) classifies **no stall of any class**, proven with direct-digest fixtures. Genuine churn — the same `chainRoot` explicitly marked `not-fixed` in two consecutive rounds — still classifies. `grep -rn "flat-trajectory\|fresh-introduced-critical"` returns no hits in `flowctl.py`, `.flow/bin/flowctl.py`, live tests, or `docs/flowctl.md`. Errors: digest-pair validation failure, truncated digests, epoch boundaries, and backend/kind switches keep today's fail-inert behavior.
- **R4:** End-to-end, all four driving the **production reservation path**: (1) the real fn-158 pair (r1: 6 fresh introduced P1; r2: those 6 resolved via the aggregate record + 1 fresh P1) reaches a normal round-3 reservation with **no stall of any class**; (2) a churn counter-case (the same `chainRoot` explicitly `not-fixed` in both rounds) still ESCALATEs; (3) a no-grammar case (rounds with zero resolution evidence) never stalls early and is bounded only by the cap; (4) **the R8 asymmetric case** — one explicit `not-fixed` in round 2 followed by a round 3 that omits it entirely (or resolves it in prose) — does **not** stall. No error surface beyond the assertions.
- **R5:** Docs: `docs/review-findings.md` ("Identity and lineage") states the literal grammar, the aggregate record, and that `unaddressed: []` is not a prior-findings signal; `docs/flowctl.md` (~`:2000`, the identity-vs-aggregate stall split) is **rewritten**, not deleted; `docs/README.md` "Notable updates" gains a bullet (precedent: the 3.14.0 convergence bullet); `docs/troubleshooting.md` root-cause list updated. CHANGELOG `## Unreleased` entry, outcome-first per `agent_docs/releasing.md`. Codex mirror regenerated (`sync-codex.sh` twice, no second-run diff). No version bump (batched). No error surface beyond the final gate.
- **R6:** **(load-bearing)** The ratchet prompt gains a regression guard against silent drift: a test extracts **every** status token and example line the emitted block advertises (never one hand-picked `fixed` case) and asserts each is accepted by `_FINDINGS_PRIOR_RE`, recognized by `_FINDINGS_PRIOR_RECORD_RE` without creating a count mismatch, and normalized by `_FINDINGS_STATUS_ALIASES`. This guard now protects **the only terminal that can still fire** — a prompt/parser divergence no longer degrades a heuristic, it silently removes stall detection entirely. Errors: none — a pure assertion.
- **R7:** `review.maxIterations` config key. **Precedence: env `MAX_REVIEW_ITERATIONS` > config > default 8.** A `>= 1` clamp on **both** paths (today the clamp lives only in the env branch); never disable-able, never 0 (fn-159 invariant). **Every self-grant route is blocked in ralph-guard with tokenized matching (never substring):** (a) `flowctl config set` naming the cap in **either** its leaf form (`review.maxIterations <n>`) **or** its parent-key form (`review '{"maxIterations":99}'` — `_set_config_locked` JSON-coerces a `{`-leading value and replaces whole subtrees, so a leaf-only screen is no screen at all) — blocked outright rather than "lowering allowed", since a human setting it once is the intended path and humans are not guard-gated, and scoped to the cap rather than all of `config set` (tracker/setup writers legitimately run under Ralph; `config set review.backend …` must still pass, positively tested); (b) file-tool writes to `.flow/config.json`, via `PROTECTED_FILE_PATTERNS`; (c) a `MAX_REVIEW_ITERATIONS=` assignment on a command — the higher-precedence route, and a **pre-existing** hole this closes. Each route gets a guard test. Resolution is memoized once per process (or resolved via the existing config snapshot) so the 7 call sites do not become 7 config round-trips. fn-138 contract honored: TABLE entry in `scripts/gen_flow_config_schema.py`, committed artifact regenerated in the same change, `test_flow_config_schema_drift` green. Precedence matrix tested explicitly: config-only, env-only, both, invalid config value, `0`/negative on each path. Errors: invalid/`0`/negative on either path falls back to the default; the guard does not fire on Cursor (prose-only degradation, same as the existing reset block), and flowctl-internal config writers are unaffected.
- **R8:** **(added at plan-review round 1 — P0)** Carried findings do not inherit an unrepeated `not_fixed`. In `_review_finding_prior_items`, a carried item at `not_fixed` is reset to `open` before this round's explicit records are applied; `fixed` and `withdrawn` are preserved. Consequence, which must hold: `same-not-fixed-lineage` fires only when the reviewer explicitly states `not-fixed` for the same `chainRoot` in **both** consecutive rounds. Tested via the production parser: explicit `not-fixed` in both rounds → stall; explicit in round 2 then omitted in round 3 → **no stall**; a `fixed` or `withdrawn` prior is never re-opened; round 1 (no carried items) is a no-op. Errors: none new — the reset happens inside the existing single pass, so a count mismatch still returns the whole-container `None` exactly as today.

## Boundaries
<!-- scope: business -->

- **`flat-trajectory` and `fresh-introduced-critical` are REMOVED**; `same-not-fixed-lineage` and the cap are the only terminals. The following consequences are **accepted, not oversights**:
  - **(a) This reverts fn-159's cost claw-back for non-repeating loops.** fn-159 built these rules to "claw back the doubled worst case of the 4→8 raise." Honest framing: a bounded insurance premium — worst case single-digit-millions of tokens on a genuinely pathological loop (observed: one codex plan-review = 0.9–1.8M input tokens) — paid to stop taxing healthy loops, which field data says are the overwhelmingly common case. `MAX_REVIEW_ITERATIONS` / `review.maxIterations` is the tuning knob if the premium bites: **lower the cap, never re-add inference.**
  - **(b) Non-repeating churn loses early detection entirely** and is cap-bounded by design. *This is the regression vector* — stated explicitly so nobody re-adds a trend rule.
  - **(c) Backend switches lose all early detection.** `same-not-fixed-lineage` is gated on `same_identity`; `flat-trajectory` was the aggregate fallback that stayed live across switches. Switches are now cap-only.
  - **(d) Host is cap-only in practice.** Host produces no lineage evidence without grammar compliance, and nothing enforces a host reviewer's compliance. The Open Question about host enforcement rises from "nice to have" to "the only backend with no stall coverage."
  - **(e) A `not_fixed` status no longer survives an unrepeated round (R8).** The digest's status column becomes a statement about *this* round only, so the rendered prior-findings block loses the "you called this unfixed last round" nuance. Accepted: that is prompt copy, not evidence, and the alternative is a new per-round-verification digest field this spec forbids.
- No new receipt schema fields and no digest-shape change (verified achievable). R8 changes carried status *values*, not the schema or the row shape.
- No relaxation for a genuinely repeating reviewer: an explicit `Prior finding #N: not-fixed` in two consecutive rounds still stalls exactly as today.
- Not a rewrite of the findings container, lineage model, or fixture-corpus format.
- Not host-reviewer *compliance enforcement* — fn-168 fixes host wording only (see Open Questions).
- Not the PR review-bot channel. PR bot comments (e.g. `chatgpt-codex-connector`) are a separate channel, deliberately out of blast radius per fn-159: they do not participate in the findings container, digest, lineage, or any flowctl guard, and their bound is `land.ciFixBudget` + unresolved-thread count + the patience window, all owned by `/flow-next:land`.

## Strategy Alignment

Active tracks served:
- **Ralph autonomous mode** — convergence-aware review terminals are a named pillar of the autonomy track ("multi-model review at every handover, convergence-aware review terminals … don't-thrash reflexes"). A false stall at round 2 is precisely the thrash-reflex misfiring against a healthy loop, and it forced human hand-verification three specs in a row.
- **Self-improving through normal work** — graduated directly from field evidence (live digests, three escalations, and a failed first fix that proved the second class does the same thing) plus an existing memory entry describing this exact parser class.

## Decision Context

### Why delete both classes rather than fix them

The historical hinge is `get_max_review_iterations()`'s own docstring, which motivated building these heuristics in the first place:

> The cap counts *dispatches*, which cannot distinguish a loop that is genuinely stuck from one converging in severity while each fix surfaces one more small thing. Field evidence: in a single session three specs hit the cap at 4, and in every case the findings remaining were trivial residue - two were reset by a human and shipped almost immediately after.

That observation is right, and it is also what now retires the heuristics: **the answer was better evidence, not better inference.** Both deleted classes were round-local snapshots inferring convergence from data the parser never reliably captured; the survivor reads an explicit reviewer statement. Empirical record: **3 recorded false positives (fn-156, fn-157, fn-158) vs 0 recorded true positives** for either deleted class.

**Honest caveat:** churn IS real — memory `pr-bot-review-loops-do-not-converge-2026-08-04` documents non-convergence in the wild — but in the **PR channel**, bounded by `land.ciFixBudget`, not by these rules. "We deleted the rules" must not be read as "we decided churn is a myth."

Recorded because it partially retires a **shipped** spec's acceptance contract: **fn-159 R2 enumerates all three stall rules with exact math and is hereby superseded** for the two deleted classes.

### Why the amended aggregate signal rather than `unaddressed: []`

That key is ambient (emitted in every review, including round 1 where no priors exist) and answers R-ID coverage, not finding resolution. Sweeping priors off it would erase the only evidence the surviving terminal reads — converting a loud false stall into a silent, permanent loss of stall detection. See the Architecture section for the two observed transcript tails. Recorded because it contradicts the spec as originally authored.

### Why `review.maxIterations` is in scope

Consequence (a) tells future maintainers to lower the cap instead of re-adding inference. Today that instruction is unreachable in practice: the cap is env-only, unpersisted, and absent from the published schema. Shipping the advice without the valve would guarantee the advice is ignored.

### Why carried `not_fixed` is reset rather than trusted (R8)

Recorded because it contradicts this spec as re-planned: the delete-both argument rested on "`not_fixed` is written only by an explicit reviewer statement", and that is true only of the round in which the statement was made. Carry-forward propagates the value verbatim, so the survivor could fire on a pair of rounds where just one carried a statement — reproducing, inside the survivor, the exact silent false-stall being deleted. Resetting `not_fixed` to `open` at carry-forward makes the premise literally true: the lineage intersection now requires the reviewer to say "still broken" twice. `fixed`/`withdrawn` are exempt because they are resolved terminals, not open claims.

### Why the guard covers three routes, not one

The `.5` valve was originally justified as closing a self-grant path "the env var never was". That was wrong in the direction that matters: `MAX_REVIEW_ITERATIONS=99` on a command is *higher* precedence than config and is not screened today, and `.flow/config.json` is not in `PROTECTED_FILE_PATTERNS`, so a file-tool write reaches it. Shipping a durable config key with only the `config set` verb blocked would have been a net regression against fn-159's invariant. Recorded because it contradicts the spec as re-planned, and because closing the env hole is a scope addition the field evidence justifies.

Round 2 then found the screen itself under-specified: `config set` accepts a JSON object for a parent key (`_set_config_locked` coerces a `{`-leading value and replaces whole subtrees), so `config set review '{"maxIterations":99}'` sets the cap without naming the leaf key. A screen matched on the leaf key alone would have shipped as security theatre. Recorded because "block the config-set path" read as sufficient and was not.

### Corrections carried forward from earlier plan-review rounds

Recorded because they contradict the plan as first written: (a) R3's original predicate — "require ≥1 re-affirmed or fresh open finding" — does NOT fix the named regression, because the fn-158 shape contains a fresh finding and the 7-vs-6 comparison still stalls; (b) the mandated `not-fixed` spelling and the `Prior findings: all fixed` aggregate are both rejected by `_FINDINGS_PRIOR_RE` today while matching the broad record regex, so advertising them without widening the parser vocabulary would drop entire findings containers, reproducing the bug class; (c) the fixture corpus is rooted at repo-root `optimization/reached-path/`, not under `plugins/flow-next/`; (d) task `.1` originally advertised tokens whose parser support lived in the dependent task `.2` — an impossible order — so vocabulary/recognition moved INTO `.1`.

### Why fn-168 before fn-166

fn-166 moves this code wholesale with zero behavior change and has not started; landing a small fix first costs fn-166 a rebase, whereas the reverse entangles a behavior fix with a large mechanical extraction mid-flight.

## Early proof point

Task `.3` (the deletion) validates the core claim and **depends on nothing**: its tests write digest rows directly (`self._digest(self._carried(...))`), so it can assert the fn-158 shape (6 fresh introduced P1 → 6 carried `fixed` + 1 fresh P1) classifies **no stall of any class** without `.1` or `.2` landing. If deleting both classes turns out to leave a genuine-churn case uncovered that the team is unwilling to send to the cap, the delete-both decision must be reopened before the prompt/parser work is worth landing. A proof point scheduled last would be a proof point in name only.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Prompt grammar + parser vocabulary + host wording; compliant-response fixture | .1 (prompt/vocabulary/host), .2 (production-parser fixture) | — |
| R2 | Dedicated aggregate all-clear record, scoped + explicit-wins, `unaddressed` negative-tested | .2 | — |
| R3 | Delete both inference classes; fn-158 shape no longer classifies; churn still does | .3 | — |
| R4 | Four production-reservation-path e2e cases (incl. the R8 asymmetric case) | .4 | — |
| R5 | Docs + flowctl.md rewrite + Notable updates + troubleshooting + CHANGELOG + mirror | .4 | — |
| R6 | Prompt/parser drift guard over every advertised token | .1 | — |
| R7 | `review.maxIterations` + all 3 ralph-guard routes + memoization + fn-138 schema contract | .5 | — |
| R8 | Carried `not_fixed` reset at carry-forward; lineage needs an explicit statement in both rounds | .2 (semantics), .4 (e2e asymmetric case) | — |

## References

- `plugins/flow-next/scripts/flowctl.py` — `_review_stall_rule` (~:11187), `_review_stall_marker` (~:11307), `enforce_and_increment_review_cap` (~:10891) / `_enforce_and_increment_review_cap_locked` (~:11325, stall consult ~:11598), `_review_finding_prior_items` (~:5134-5207, sole call site ~:5476), `_FINDINGS_STATUS_ALIASES` (~:4577) / `_FINDINGS_PRIOR_RE` (~:4625) / `_FINDINGS_PRIOR_RECORD_RE` (~:4639), `build_convergence_ratchet_block` (~:11827, rule 1 ~:11880), `_render_structured_prior_finding` (~:11780), `build_rereview_preamble` (~:11934), `build_review_findings_digest` (~:5954-5984), `get_max_review_iterations` (~:9556), `get_default_config` (review block), `load_config_snapshot` (~:1637), `REVIEW_JSON_TALLY_BLOCK` (~:8893, PINNED), `status: "open"` creation writes (~:4920, :5540, :5123), journal recovery rows (~:9854, :9870)
- Ratchet call sites (5, one builder; host does NOT use it): ~:39562, :40433, :40920, :41185, :41235
- `plugins/flow-next/skills/flow-next-impl-review/workflow-host.md` (~113-118), `flow-next-plan-review/workflow-host.md` (~83-84), `flow-next-spec-completion-review/workflow-host.md` (~130-133)
- Guard: `plugins/flow-next/scripts/hooks/ralph-guard.py` (recovery screens ~:702-738, ~:1200-1234; argv pass ~:1340-1370)
- Schema: `scripts/gen_flow_config_schema.py` (descriptions ~:58, TABLE ~:561-572)
- Tests: `test_review_convergence_cap.py` (`TestConvergenceRatchet` ~:86; stall assertions ~:4295-4472), `test_review_findings_parser.py` (grammar accept/reject ~:368-437), `test_review_findings_fixture_corpus.py` (matrix ~:37), `test_review_findings_receipts.py`, `test_review_json_tallies.py`, `test_prompt_text_pinned.py` (`PROMPT_HASHES` ~:89), `test_flow_config_schema_drift.py`
- Fixtures (repo root, NOT under plugins/): `optimization/reached-path/fixtures/review-findings/v1/<backend>/<case>.md` + `INDEX.json` (6 backends)
- Docs: `plugins/flow-next/docs/review-findings.md` (~100-121), `docs/README.md` "Notable updates" (~54-70), `docs/troubleshooting.md` (~83), `docs/flowctl.md` (~2000)
- Memory: `bug/runtime-errors/structured-review-parsers-must-2026-07-30` (this exact class), `bug/test-failures/test-production-path-not-parallel-construction-2026-05-21`, `knowledge/workflow/pr-bot-review-loops-do-not-converge-2026-08-04`, `knowledge/decisions/shell-command-allowlist-gates-must-2026-06-05`, `knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30`
- Coordination: fn-166 (extraction of this region — land fn-168 first), fn-159 (the superseded stall-rule contract)

## Open Questions

- **Host-reviewer compliance — now the only backend with no stall coverage (raised in priority by this design, still not blocking).** Host rounds never pass through the ratchet builder, so even after the wording fix a host reviewer that ignores the grammar produces no lineage evidence and is bounded only by the cap. fn-168 fixes the wording in all 3 files; whether host needs its own enforcement (structured reply contract, or a rounds-carried ceiling) is a follow-up spec.
- Should the ratchet prefix/suffix be promoted to module-level pinned constants (bringing them under `test_prompt_text_pinned`) rather than covered by R6's targeted assertion? R6 is the cheaper guard; promotion is a larger, hash-churning change. Decided in task `.1` if it turns out to be a one-liner.
