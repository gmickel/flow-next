---
satisfies: [R3, R5]
---
# fn-138-published-json-schema-for-flow-config.3 Setup schema stamping + docs

## Description
$schema stamping + documentation + convergence.

**Size:** S

### Approach
- Setup writes `$schema` (stable URL `https://flow-next.dev/schema/flow-config.schema.json` - latest-mutable, not versioned) into configs it scaffolds/refreshes via the cmd_init write paths (_init_persisted_defaults on absent config; deep-merge rewrite on re-init); existing configs untouched otherwise; both setup modes honored; offline-tolerant (inert string, flowctl never fetches it).
- Docs: flowctl.md config section links the schema AND corrects the wrong default rows (memory.enabled, planSync.enabled - documented false, code default true); Unreleased CHANGELOG; downstream-walk note lists the docs-site publication of the schema file at the stable URL BEFORE the release announcement (until published, editors show a transient could-not-load-reference warning - accepted, noted in the CHANGELOG entry).
- Full suite + smoke where touched.

## Acceptance
- [ ] Stamping on scaffold/refresh only; docs + Unreleased + walk note; full gate green (R3, R5).

## Done summary
flowctl init now stamps "$schema" (first key, ONE constant FLOW_CONFIG_SCHEMA_URL) on both cmd_init write paths - fresh scaffold and deep-merge re-init refresh - pointing at the published URL; existing configs untouched on every other path, existing values survive, config set round-trips the stamp (all covered by new test_init_schema_stamp.py incl. idempotency/no-duplicate-keys/ordering). Docs: flowctl.md config section links the committed schema artifact + published URL and corrects the memory.enabled/planSync.enabled default rows (false -> true); setup workflow one-clause note (codex mirror regenerated); Unreleased CHANGELOG entry with the transient editor-warning note and the publish-schema-before-announcement downstream-walk note. Full gate green (run_tests_parallel 3567 tests, ruff clean); reached-path evidence pins refreshed for the workflow.md delta per the fn-137/fn-139 maintenance pattern.
## Evidence
- Commits: 090e7b009952d5e3b4eef048191082442d678c9b, 6830c8254eccdab0ae172e2670c359add63f72c2, 9524c7a9
- Tests: baseline: green (focused: test_flow_config_schema, test_flow_config_schema_drift, test_init_crossspec_mirror, test_artifacts_config, test_config_snapshot; gen_flow_config_schema.py --check current), cd plugins/flow-next/tests && python3 -m unittest test_init_schema_stamp test_flow_config_schema_drift test_flow_config_schema test_startup_bootstrap test_tracker_distribution test_setup_reference_routing -q, python3 scripts/gen_flow_config_schema.py --check, python3 scripts/run_tests_parallel.py (suite_rc=0, files=168 ran=3567 failures=0 errors=0; green receipt .flow/tmp/green-receipts/6830c825-unittest.json), uvx ruff@0.16.0 check . (All checks passed)
- PRs: