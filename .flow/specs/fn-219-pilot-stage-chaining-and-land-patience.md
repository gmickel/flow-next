# Pilot stage chaining and land patience-after-review, opt-in idle removal

## Goal & Context

Wall-clock finding #7 of the flow-next wall-clock research (vault note `flow-next - Wall-Clock Research (2026-08 Pass 2)`): two autonomous loops idle for whole loop intervals on transitions whose outcome is already decided. Both fixes are opt-in configuration, change no gate, and owe no eval — the research record settles that (no conditional knobs was ruled for *quality* topologies; these are idle-removal switches that leave every verdict, gate, and merge license untouched).

**Part A — pilot stage chaining.** Pilot advances exactly one stage per tick. The research finding named two deterministic follow-ups, `plan` → `plan-review` and `qa` → `make-pr`. Plan review (fn-219 plan review, codex) dissolved the first: pilot dispatches `plan` with `--review=<backend>`, and the plan skill's own Step 7 runs the plan-review fix loop to SHIP inside that dispatch, so after a successful autonomous plan the next classification is already `work` — there is no idle interval to remove, and a chained plan-review would be a second paid review of an unchanged artifact (or a `NOT_RETRYABLE` terminal when the embedded loop did not ship). The one real idle is `qa` → `make-pr`: every fresh terminal QA outcome advances to make-pr by contract, yet make-pr waits for the next driver tick and a full re-anchor. With `pipeline.chainStages` on, a tick that completed `qa` runs `make-pr` in the same tick. Nothing else chains: `plan-review` → `work` and `work` → `qa`/`make-pr` stay one-stage-per-tick, because those transitions cross a stage that can fail into human territory (a NEEDS_WORK review, an unfinished implementation, a completion gate).

**Part B — land patience after review.** Under the default `silence` review signal, a PR with a verified head-current automated review and zero unresolved threads still waits the full patience window measured from the last push, restarted by every fix push. The window exists as the human-objection grace period — time for a person to look at what the bot said and object. With `land.patienceMinutesAfterReview` set, and only when the latest automated review event is head-current with zero unresolved threads, the silence gate's wait is that many minutes measured from the review event instead of from the push. Unset keeps today's behaviour byte-for-byte.

Target user: whoever runs pilot + land unattended under a host `/loop` and is paying loop intervals for transitions that need no judgment.

## Architecture & Data Models

Both parts are skill-prose changes plus one seeded config default each; flowctl stores and serves the keys and never interprets them (the split rule: flowctl owns "set this field", the skill owns "read it and act").

**Config keys (seeded in the shipped defaults, published in the JSON schema):**

- `pipeline.chainStages` — string-enum `off | on`, default `off`, sibling of `pipeline.qa` and read with the same strict-literal discipline: only the literal `on` activates; `off`, null, bool `true`, or any other value is off. Read once per tick from pilot's root config snapshot (the fn-110 single-`config get` contract stands: SKILL.md owns the one config call, workflow.md derives via jq). A snapshot read error resolves to off (fail-closed — chaining is an accelerator, so the safe degradation is today's one-stage tick).
- `land.patienceMinutesAfterReview` — integer-or-null, default `null` (unset). Active only when it reads as a positive integer; null, `""`, `0`, or a non-numeric value are off. Read through land's existing single `config get land --json` subtree capture.

**Pilot chaining (in the shared classify → branch → dispatch → verify path):**

- The chain table is closed and has one row: `qa` → `make-pr`. The chained stage is entered only when the primary `qa` stage's Phase 5 verify decided `QA_ADVANCED=true` from the fresh receipt (any fresh terminal `qa_outcome` — SHIP, NA, BLOCKED, or NEEDS_WORK — exactly the set the unchained next tick would make-pr on). `plan` → `plan-review` is deliberately absent (see Goal): the plan dispatch already embeds its review loop, so the table row would either double-review an unchanged artifact or hit `NOT_RETRYABLE`. No new config read: the gate derives from the root snapshot via jq.
- The chained make-pr runs the same phases the standalone stage runs: its branch-matrix row (the spec branch qa checked out — no second checkout), its pre-dispatch evidence (no OPEN PR, already proven by the all-done probe this tick), its dispatch with `mode:autonomous`, its own Phase 5 evidence block (gh-confirmed open PR URL) and `stage:` outcome line, and its own ledger/verdict handling. In backlog mode the dispatch allowlist assert runs before the chained dispatch (`/flow-next:make-pr` is already on the allowlist) and every dispatched stage appends its own decision-log row — a chained backlog tick writes two rows; the row-per-tick invariant becomes row-per-dispatched-stage.
- The single-dispatch prose is reconciled, not contradicted, on every authoritative surface: the pilot SKILL.md description and Forbidden bullet, the workflow header and Phase 4 "Done when", the backlog-mode reference's "advances exactly one stage" sentences, the `commands/pilot.md` description, and the two hardcoded pilot description strings in the codex sync script all keep "one stage per tick" as the rule and gain the gated clause — with `pipeline.chainStages` on, `make-pr` after a fresh `qa` verdict is the only admissible second dispatch; any other second stage still breaks the contract.
- Verdict grammar extension: `stage=` names every stage dispatched this tick in order, joined by `+` (`stage=qa+make-pr`); the verdict is the last dispatched stage's verdict; the reason names both outcomes (the fresh `qa_outcome` and the PR URL or its absence). A chained make-pr that yields no open PR records its strike under `make-pr` exactly as a standalone tick would; a crash-class outcome in the chained stage (dirty non-`.flow/` tree, gh probe failure) is `NEEDS_HUMAN` with no strike, as today, and the qa stage's already-echoed evidence block stays in the transcript. Ledger writes are sequential within the single-threaded tick — the qa `ADVANCED` clear (atomic jq+mv) completes before the chained stage's own clear or strike write — so there is no clear-versus-strike race.
- `--dry-run` stops after classification as today and additionally reports `chain=<off|on>`; when on and the classified stage is `qa` it reports `would-chain=make-pr` conditional on a fresh terminal verdict (a conditional, never a promise — dry-run dispatches nothing); when on and the classified stage is anything else it reports `would-chain=none (stage <x> heads no pair)`. Every known precondition is evaluated before a target is named, so the diagnostic never names a target the live tick would skip.
- The dry-run tick, the strikes ledger schema, backlog SELECT/TRIAGE/ASK, the QA freshness probe, and `pipeline.chainStages` off (byte-for-byte today's tick) are unchanged.

**Land patience after review (§2.6 of the land gate tree, `silence` signal only):**

- The key is read through the existing single `config get land --json` capture (`lcfg`), beside the other land reads — never a second config call.
- The reviews-API loop already decides head-currency per automated review; it additionally records `REVIEW_EVENT_AT` as the MAX `submitted_at` across every head-current automated review (a running max over the paginated loop — API page order is not newest-first, and several bots may review). The clean-review comment scan's jq projection gains `updated_at` (today it projects login and body only) and folds a qualifying comment's `updated_at` into the same max (an edited-in-place summary comment's edit time is the review event). The max is taken lexically (ISO-8601 orders lexically, the convention `LAST_PUSH` already uses); the age in minutes is computed by the same `fromdateiso8601` epoch subtraction §2.3 uses for the push anchor, with a parse failure falling back to the push anchor. `REVIEW_EVENT_AT` is a per-tick in-memory value recomputed from GitHub every tick — nothing is persisted, so the ledger schema (including `triggerSha` and the review-trigger one-shot) is untouched.
- After the review evidence is gathered and before signal evaluation, when `PATIENCE_AFTER_REVIEW` is active AND `AUTO_REVIEW_CURRENT == 1` AND `UNRESOLVED == 0` AND `REVIEW_EVENT_AT` is non-empty, the silence gate's window is re-anchored: `WINDOW_ANCHOR=review`, age measured from `REVIEW_EVENT_AT`, elapsed iff age ≥ `PATIENCE_AFTER_REVIEW`. `UNRESOLVED` is re-read every tick, so a thread that arrives after the review event fails the conjunct and the tick routes to the resolve path as today. Every other consumer of the push-anchored window keeps it: the §2.4 no-checks-registered guard, the `approve` and `<login>` signals, the §2.6b human-review-pending verdict, and the §2.7 detector all read the push window as before. A fix push moves the head, the review stops being head-current, and the gate falls back to the push anchor until the bot re-reviews — so "restarted by every fix push" holds by construction, with no new ledger state.
- The window in the `AWAITING_REVIEW` reason and the Phase 4 report names the anchor that bound: `window=<age>/<limit>m anchor=<push|review>` is emitted only when the key is configured (unset keeps today's report line byte-for-byte), with `anchor=push` on configured-but-not-due ticks — the initializer branches on the config value, never on the firing branch (the fn-200 `reviewers=off` lesson).
- The merge license is untouched: `--squash --delete-branch --match-head-commit`, never `--auto`, only after every gate passes in-tick.

## API Contracts

- `flowctl config get pipeline.chainStages --json` → `{"key":"pipeline.chainStages","value":"off"}` on a fresh repo; `flowctl config set pipeline.chainStages on` round-trips; init materializes `pipeline` as `{"qa":"off","chainStages":"off"}` and an upgrade init adds the missing leaf without touching a user-set `qa`.
- `flowctl config get land.patienceMinutesAfterReview --json` → `{"key":"land.patienceMinutesAfterReview","value":null}` on a fresh repo; `flowctl config set land.patienceMinutesAfterReview 15` persists the integer 15 (digit coercion, as `land.patienceMinutes`).
- Published schema (`flow-config.schema.json`, regenerated): `pipeline.chainStages` enum `["off","on"]` default `"off"`; `land.patienceMinutesAfterReview` type `["integer","null"]` default `null`; both carry docs-authored descriptions.
- Pilot terminal line: unchanged grammar; `stage=` additionally admits `qa+make-pr`. Stage-outcome lines: one per dispatched stage. Dry-run adds `chain=<off|on>` and, when on, `would-chain=make-pr` (classified `qa`) or `would-chain=none (stage <x> heads no pair)`.
- Land report line, key configured: `window=<AGE>/<LIMIT>m anchor=<push|review>`; key unset: the existing `window=<AGE_MIN>/<PATIENCE_MIN>m` byte-for-byte.

## Edge Cases & Constraints

- Chaining never introduces a second `gh` touch outside the sanctioned sites: the chained make-pr uses the same verification probe the standalone make-pr stage uses.
- A chained `make-pr` whose post-dispatch tree is dirty outside `.flow/` is crash-class `NEEDS_HUMAN`, as today.
- The codex mirror is regenerated once, by the final task, after every canonical prose task has landed: the sync script deletes and rebuilds the whole mirror tree, so two parallel tasks each running it would clobber each other's output. Prose tasks pin canonical files only; the final task extends the pins to the mirror copies after the regen.
- The chained make-pr under autonomous mode stays a draft PR; pilot still never invokes land or merges (R6 of backlog mode; the Forbidden list).
- Under `land.reviewSignal` `approve` or `<login>`, `patienceMinutesAfterReview` has no effect (documented: the key is a `silence` policy refinement).
- A review event later than the push can lengthen the wait relative to the push window (review at push+25m with a 20m after-review window waits until push+45m instead of push+30m): the window is grace *after the review*, by design, and the docs say so.
- `patienceMinutesAfterReview` shorter than the time a bot needs to review is harmless: until a head-current review exists the push window governs.
- Neither key changes any Ralph, Cursor, Codex, Droid, Grok, or OpenCode host behaviour differently from Claude Code: both are skill prose consumed as-is by every host, so `platforms.md` needs no note.
- Prose growth is bounded (G1): the pilot chain is written once as a one-row table plus a short chained-dispatch paragraph that references the existing make-pr phases rather than restating them, plus one clause per single-stage surface; the land change is one anchor block plus two report tokens. The G1 justification: each sentence either states a contract the tests pin or a rule the executing agent needs to avoid crossing into a non-chainable stage.
- Task ordering: the two prose tasks depend on the config task (the early proof point), then run in parallel on disjoint files; the docs task depends on all three and owns the single mirror regeneration.

## Acceptance Criteria

- **R1:** `pipeline.chainStages` is a seeded string-enum default `off`; only the literal `on` activates chaining (bool `true`, null, typos read as off); `config get`/`set` round-trip and init materializes/upgrades the leaf beside `pipeline.qa` without clobbering a user-set sibling. Errors: no error surface beyond the existing `config set` path.
- **R2:** `plan` → `plan-review` is NOT a chain pair: a tick whose `plan` stage advanced ends exactly as today (`ADVANCED ... stage=plan`), because the plan dispatch already embeds the plan-review loop. The chain table in the pilot workflow names `make-pr` as its only target and never names `plan-review`. Errors: no error surface beyond today's plan stage.
- **R3:** With `pipeline.chainStages` on, a tick whose `qa` stage verified `QA_ADVANCED=true` (any fresh terminal `qa_outcome`) dispatches `make-pr` in the same tick on the spec branch, verifies via the gh open-PR probe, emits a second evidence block and `stage:` outcome line, and ends `PILOT_VERDICT=<verdict of make-pr> spec=<id> stage=qa+make-pr`; the PR stays draft under autonomy. Errors: missing/stale QA receipt → no chain (the standalone healthy-no-advance strike path, `stage=qa`); make-pr yielding no open PR → strike under `make-pr`; dirty tree or gh probe failure → `NEEDS_HUMAN`, no strike.
- **R4:** No other transition chains: `plan`, `plan-review`, `work`, and `make-pr` are never chained from, and `work` is never chained into. Off (default) leaves the chain path unentered and the tick's stage set, classification, ledger, and verdict grammar unchanged; the one deliberate behaviour change that ships regardless of the switch is the make-pr verify-probe hardening recorded in Decision Context (a `gh` or parse failure at the verify is crash-class `NEEDS_HUMAN`, no strike, for standalone and chained ticks alike). Every authoritative "one stage per tick" surface (pilot SKILL.md and workflow, backlog-mode reference, `commands/pilot.md`, the sync script's two hardcoded pilot descriptions) carries the gated clause rather than contradicting it. Backlog-mode SELECT/TRIAGE/ASK are unchanged; a chained stage in backlog mode appends its own decision-log row and passes the dispatch allowlist assert. Errors: none beyond R3.
- **R5:** `--dry-run` still stops after classification and reports `chain=<off|on>` plus `would-chain=make-pr` only when the classified stage is `qa` (conditional on a fresh terminal verdict), else `would-chain=none (stage <x> heads no pair)`; no dispatch, no ledger write. Errors: none.
- **R6:** `land.patienceMinutesAfterReview` is a seeded null default; `config get` returns null on a fresh repo; `config set` persists an integer; the land Phase 0 read treats null, `""`, `0`, and non-numeric as off. Errors: no error surface beyond the existing `config set` path.
- **R7:** Under `silence`, when the key is active and the latest automated review event is head-current (reviews-API `commit_id == HEAD_OID` or submitted after the last push; or a qualifying clean-review comment naming the head) with zero unresolved threads, the silence gate's window is measured from that review event with the configured limit; otherwise the push-anchored window applies unchanged. A fix push (new head) reverts to the push anchor until a new head-current review exists. Errors: unparseable review timestamp → push anchor (fail-safe to today's wait).
- **R8:** Only the silence signal's window conjunct re-anchors: `approve`/`<login>` signals, the no-checks-registered guard, the human-review-pending verdict, and the stale-approval detector keep the push window. The merge call is unchanged (`--squash --delete-branch --match-head-commit`, never `--auto`). Errors: none.
- **R9:** Report and reason lines name the binding anchor when the key is configured (`anchor=<push|review>`, initialized from the config value so a configured-but-not-due tick reports `anchor=push`); unset leaves the report line byte-for-byte. Errors: none.
- **R10:** Docs updated in the same change: `flowctl.md` config table rows for both keys; `orchestration.md` "Chaining the loops" explains in-tick chaining and the review-anchored window; `running-lean.md` prices both options in structural terms under the autonomous-loops layer and says why patience-after-review stays opt-in (the window is the human-objection grace period); pilot and land SKILL.md and the conduct checklists reflect the new contracts; schema regenerated; codex mirror regenerated twice; CHANGELOG `## Unreleased` entry user-outcome first. Errors: none.
- **R11:** Tests assert behaviour or contract (G2): config default/round-trip/init tests for both keys; schema byte-identity and drift stay green; static contract pins over the skill files limited to the smallest distinctive tokens (the snapshot-derived jq key, the `qa+make-pr` stage token, the absence of a `plan-review` chain target inside the chain block, the land `lcfg` read, the anchor conjunct on `AUTO_REVIEW_CURRENT`/`UNRESOLVED`, the unchanged merge flags), pinned on canonical files by the prose tasks and extended to the mirror copies by the final task after the single regen. No prose-sentence assertions, no size baselines. Errors: none.

## Boundaries

- No chaining of `plan → plan-review` (dissolved: the plan dispatch embeds its review), `plan-review → work`, `work → qa`, or `work → make-pr`; no "chain everything" mode; no per-pair knobs (one switch, closed table).
- No change to the strikes ledger schema, the QA freshness probe, backlog SELECT/TRIAGE/ASK, or pilot's never-merge/never-land rule.
- No change to `land.patienceMinutes` semantics, to the `approve`/`<login>` signals, to the merge command, or to the land ledger schema; no new ledger field.
- No eval; no version bump; no merge of the PR.
- No platforms.md note (host behaviour identical); no Ralph harness changes.
- The docs-site (flow-next.dev) update rides the same workstream but is a separate repo commit, not part of this PR.

## Decision Context

- Both switches are idle removal, not quality topology: the wall-clock record's "no conditional knobs / dual topologies" ruling covers review shapes; here every gate, verdict, and merge license is unchanged with the switch on or off, which is why no eval is owed.
- Chain table is closed and minimal by construction: `qa → make-pr` is the only transition where the next tick's classification is fully determined by the current stage's success AND an idle interval exists today. `plan → plan-review` was dropped at plan review (codex, round 1, P0): pilot's plan dispatch passes `--review=<backend>` and the plan skill's Step 7 runs the plan-review loop to SHIP inside the dispatch, so a successful plan tick already leaves `plan_review_status=ship` and the next classification is `work`; a chained plan-review would be a second paid review of an unchanged plan or a `NOT_RETRYABLE` terminal — the research finding's premise for that pair does not hold under current mechanics (the same way finding #6 dissolved). Reinstating it is a human decision that would first need the plan dispatch to stop embedding its review. `plan-review → work` was rejected because a NEEDS_WORK review is a human-territory outcome; `work → qa/make-pr` because work's completion gate can route back to work.
- Make-pr verify-probe hardening is a shared fix, not a chain-only branch (impl review on task .2, all three axis draws, settled): the standalone verify piped `gh` through `jq | head`, so an outage or malformed response read as "no PR" and recorded a strike (two unready the spec). Confining the status capture to the chained path would leave the standalone tick with the false-strike bug the review found; the probe is one block used by both paths, and a probe failure now routes to the same crash-class `NEEDS_HUMAN` pilot already uses for its classification probe. Recorded in the CHANGELOG under Fixed.
- Consequence for the chain switch's reach: with `pipeline.qa` off, `pipeline.chainStages` has nothing to chain and the tick is byte-for-byte today's; the switch earns its keep only on repos running the QA stage. Documented as such rather than widened.
- `qa → make-pr` chains on every fresh terminal `qa_outcome`, including NEEDS_WORK: the unchained next tick does exactly that (QA is advisory; the draft PR is how findings are surfaced), so stopping at NEEDS_WORK would delay the surfacing it exists to provide. Recorded here so it is not re-litigated as "qa passes means SHIP only".
- Chaining lives in the shared dispatch/verify path rather than ready mode only, so backlog mode's workable route gets it too; "backlog mode unchanged" means its SELECT/TRIAGE/ASK phases and safety invariants, which are untouched. Each chained stage writes its own decision-log row because the row is per dispatched stage, and hiding a dispatched stage from the log would break the transcript-blind driver contract.
- The verdict is the last dispatched stage's verdict with `stage=` naming both: a driver grepping `PILOT_VERDICT=ADVANCED` keeps working, and a strike on the chained stage is recorded exactly as the unchained next tick would have recorded it.
- Patience-after-review replaces the push window (measured "from the review event instead") rather than taking the minimum, because the window is grace after the reviewer spoke; a late review lengthening the wait is the documented consequence. Restricting the re-anchor to the silence gate's own conjunct keeps every other window consumer byte-for-byte, which is what makes the change gate-neutral.
- No new ledger state: head-currency of the review already encodes "since the last push", so a fix push resets the anchor by construction.
- Off states: `0` is off for `patienceMinutesAfterReview` (a zero grace period is the strict-silence anti-pattern the window exists to prevent), documented in the config table.
- Sequencing with open work (spec-scout): fn-149 (land stacked-PR hardening) touches the same §2.6/§2.7 window region and fn-150 (pilot dependent-spec stacking) the same classify→dispatch path — neither is a dependency; whichever lands second rebases. fn-61 (Ralph v2, deferred) parses terminal verdict lines and will need the `+`-joined `stage=` shape when un-deferred (FYI, not gating).
- Rejected: per-pair switches or a "chain everything" mode as overkill — one closed table, one switch; taking min(push, review) for the land window as a hidden second semantics — "instead" is the contract.

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** — pilot + land are the track's default path; both switches remove idle intervals from that path while keeping the track's invariants (readiness as the consent boundary, never-merge in pilot, gated merge in land, don't-thrash reflexes) byte-for-byte.

## Early proof point

Task fn-219-pilot-stage-chaining-and-land-patience.1 validates the config surface (both keys seeded, schema regenerated, drift comparator green). If it fails, re-evaluate the off-state contracts (string-enum vs null) before the prose tasks build on them.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | `pipeline.chainStages` seeded string-enum, strict `on` | .1 | — |
| R2 | no plan → plan-review chain (dissolved) | .2 | — |
| R3 | qa → make-pr chain on any fresh terminal qa outcome, draft PR | .2 | — |
| R4 | closed table, off byte-for-byte, all single-stage surfaces reconciled, backlog rows per stage | .2 | — |
| R5 | dry-run reports chain gate + precondition-checked would-chain | .2 | — |
| R6 | `land.patienceMinutesAfterReview` seeded null, off states | .1, .3 | — |
| R7 | silence window re-anchored to head-current review event | .3 | — |
| R8 | only the silence conjunct re-anchors; merge license unchanged | .3 | — |
| R9 | `anchor=` reporting, initializer discipline | .3 | — |
| R10 | docs, conduct, schema, mirror, CHANGELOG | .2, .3, .4 | — |
| R11 | behaviour/contract tests only (G2) | .1, .2, .3 | — |

## Quick commands

- `cd plugins/flow-next/tests && python3 -m unittest test_pipeline_qa_config test_land_config test_flow_config_schema test_flow_config_schema_drift test_skill_prose_diet -q`
- `python3 scripts/gen_flow_config_schema.py --check`
- `./scripts/sync-codex.sh` twice, idempotent
- `uvx ruff@0.16.0 check .`
