---
satisfies: [R7]
---
# fn-195-orchestration-by-intent-named-tiers-per.4 Record what actually ran, so prose routing is checkable

## Description
Where the harness exposes it, record the model that executed a stage on the receipt surface that already carries review provenance. Recording only - nothing prescribes, nothing fails.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (the stage-receipt and review-attempt writers), the receipt schema documentation in the docs tree
**Touches:** [plugins/flow-next/scripts/flowctl.py, plugins/flow-next/docs/review-findings.md]

### Approach
- Extend the existing provenance rows rather than adding a second store. Review attempts already carry work-volume and head-origin fields; a stage's executing model belongs in the same shape.
- Absence is a first-class value: a harness that cannot report which model ran records unknown, never the configured or preferred value. Recording a preference as if it were an observation is exactly the fabrication this surface exists to prevent.
- No new verb and no new file. If it does not fit the existing receipt shape, stop and report rather than inventing a parallel record.
- Read-only consumers (the autonomous loop, the merge gate) must not change behavior because a new optional field appeared.

### Investigation targets
**Required** (read before coding):
- the review-attempt row writer and its optional-field conventions - absence means unknown, never zero
- the merge-gate and loop consumers of those receipts - the compatibility surface

### Acceptance
- [ ] Stage receipts record the executing model where the harness exposes it, unknown where it does not
- [ ] No new store, no new verb; existing consumers behave identically
- [ ] A preference is never recorded as an observation
- [ ] Focused suites green: review-attempt, receipt-schema and merge-gate tests

## Acceptance
- [ ] TBD

## Done summary
R7 recording surface: the fn-178 stage-outcome grammar now accepts an optional trailing `(model: <what ran>)`, and `flowctl usage --stages` aggregates a per-stage `models` tally — observed values from the annotation and from the model review receipts already carry (fn-193), everything else `unknown`. Selector placeholders (`auto`/`default`/`unknown`/blank) normalize to `unknown` so a preference is never stored as an observation; `review-rounds record` deliberately keeps NO `--model` flag (fn-193 #338: a narrating agent's claim is not an observation, pinned by test_rp_recorded_row_claims_no_model). Recording only: additive optional keys, no new store, no new verb, no consumer branches on it. Documented under "Execution provenance" in docs/review-findings.md.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)


Post-review conductor fixes (965648022c2c6b9a210eea33c506d634cdc4fd19): receipt_models split from stage-line models tally, accepted-on-read docs clause, combined-source regression test; emitter prose routed to .5 (Touches + acceptance extended).

stage: impl-review - ran (host backend, fresh fable-5 reviewer, SHIP round 1 with 2 P2 + 1 P3 suggestions applied by conductor)stage: plan-sync - ran (drift: no; .5 already carries the emitter scope; review-findings.md fully documented by .4; cross-spec deferred to conductor)

## Evidence
- Commits: 38220479889cbafc1616e148b58cad112581c5ca, 965648022c2c6b9a210eea33c506d634cdc4fd19
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_stage_model_provenance test_usage_stages test_review_findings_docs test_review_convergence_cap test_tracker_distribution test_startup_bootstrap -q, python3 scripts/run_tests_parallel.py (files=192 ran=4386 failures=0 errors=0), uvx ruff@0.16.0 check ., post-fix focused: test_stage_model_provenance test_usage_stages test_review_convergence_cap test_startup_bootstrap (243 tests OK); ruff clean, impl-review: host backend SHIP round 1 (reviewer claude-fable-5, fresh subagent; receipt /tmp/impl-review-receipt-fn-195-orchestration-by-intent-named-tiers-per.4.json)
- PRs: