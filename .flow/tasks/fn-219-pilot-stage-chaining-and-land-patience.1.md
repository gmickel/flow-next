---
satisfies: [R1, R6]
---
# fn-219-pilot-stage-chaining-and-land-patience.1 Seed pipeline.chainStages and land.patienceMinutesAfterReview defaults, schema, config tests

## Description
Add the two config keys as seeded defaults (R1, R6), publish them in the JSON schema, and extend the config test suites. Split as the deterministic flowctl half so the two skill-prose tasks can run in parallel against settled key names and off-state contracts.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `scripts/gen_flow_config_schema.py`, `plugins/flow-next/schema/flow-config.schema.json` (regenerated, never hand-edited), `plugins/flow-next/tests/test_pipeline_qa_config.py`, `plugins/flow-next/tests/test_land_config.py`
**Touches:** [plugins/flow-next/scripts/flowctl.py, scripts/gen_flow_config_schema.py, plugins/flow-next/schema/flow-config.schema.json, plugins/flow-next/tests/test_pipeline_qa_config.py, plugins/flow-next/tests/test_land_config.py, plugins/flow-next/scripts/flowctl_tracker/manifest.json]

### Approach
- `get_default_config()`: `pipeline` becomes `{"qa": "off", "chainStages": "off"}` (string-enum, comment in the style of the existing `pipeline.qa` block at `flowctl.py:1538-1551`); `land` gains `"patienceMinutesAfterReview": None` beside `patienceMinutes` (`flowctl.py:1450-1452`; extend that comment: the after-review key re-anchors the silence gate's window to the head-current review event; null/""/0/non-numeric = off). No write-time validator (matches `pipeline.qa`; the read side is strict).
- `gen_flow_config_schema.py`: DESCRIPTIONS entries modelled on `pipeline.qa` (`:379-390`) and `land.requestReviewers` (`:350-359`) — state the strict literal `on`, the off states, and the running-lean pointer; TABLE rows `("pipeline.chainStages", {"enum": ["off", "on"]})` beside `pipeline.qa` (`:669`) and `("land.patienceMinutesAfterReview", {"type": ["integer", "null"]})` beside `land.requestReviewers` (`:650`). Regenerate with `python3 scripts/gen_flow_config_schema.py`, then `--check`.
- Tests (G2 — behaviour only): update the exact-dict assertions (`test_land_config.py:104-124`, `test_pipeline_qa_config.py` `test_defaults_dict_has_pipeline_block` + the two init-materialization tests) and add: fresh `config get` returns `"off"` / `null`; `set pipeline.chainStages on` round-trips; `set land.patienceMinutesAfterReview 15` persists int 15 (digit coercion, `flowctl.py:2051`); `set ... null` reads back null; setting one key keeps sibling defaults; init upgrade adds the missing leaf without clobbering a user-set `pipeline.qa`.
- flowctl.py changed → run `python3 scripts/gen_tracker_manifest.py` and commit the manifest with the change (test_tracker_distribution).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:1440-1460` and `:1538-1551` — the land and pipeline default blocks + comment conventions
- `scripts/gen_flow_config_schema.py:340-395` and `:640-670` — sibling DESCRIPTIONS/TABLE rows
- `plugins/flow-next/tests/test_pipeline_qa_config.py` — the suite to extend
- `plugins/flow-next/tests/test_land_config.py:74-160` — defaults + round-trip patterns

**Optional** (reference as needed):
- `plugins/flow-next/tests/test_flow_config_schema_drift.py` — the defaults↔TABLE comparator that fails on a missing row
- `.flow/memory/bug/build-errors/docs-activation-command-for-string-enum-2026-06-05.md` — string-enum activation pitfall

### Acceptance
- [ ] `flowctl config get pipeline.chainStages --json` → `"off"`; `land.patienceMinutesAfterReview` → `null` on a fresh repo
- [ ] `set`/`get` round-trips (`on`; integer 15; `null`) and sibling defaults untouched
- [ ] Schema regenerated; `python3 scripts/gen_flow_config_schema.py --check` passes; `test_flow_config_schema` + `test_flow_config_schema_drift` green
- [ ] `python3 scripts/gen_tracker_manifest.py` run and committed
- [ ] Quick: `cd plugins/flow-next/tests && python3 -m unittest test_pipeline_qa_config test_land_config test_flow_config_schema test_flow_config_schema_drift -q`

## Acceptance
- [ ] TBD

## Done summary
Seeded `pipeline.chainStages` (string-enum, default `"off"`, strict-literal `on`) beside `pipeline.qa` and `land.patienceMinutesAfterReview` (default `null`; null/""/0/non-numeric = off) beside `land.patienceMinutes` in `get_default_config()`; published both in `gen_flow_config_schema.py` (DESCRIPTIONS + TABLE) and regenerated `flow-config.schema.json`; regenerated the tracker MANIFEST. Tests (R1, R6): fresh-get defaults, set/get round-trips (`on`; int 15; `null`/""/0 persisted verbatim), a strict-literal predicate table (bool `true`, `null`, `On`, `yes` all read off), sibling-default preservation both ways, and an upgrade init that adds the `chainStages` leaf without clobbering a user-set `pipeline.qa` (tests: test_pipeline_qa_config `test_*chain_stages*`, test_land_config `test_*patience_after_review*`). Baseline green; codex mirror untouched by design (no scripts mirrored; the .4 docs task owns the single regen).

stage: impl-review - ran [round 1 fan-out (correctness SHIP, contracts NEEDS_WORK P3 comment contradiction, integration SHIP) .. round 2 re-review SHIP]
## Evidence
- Commits: 8cd8b0bba2c54e126ccc82de113b24aa8b572bb3, c21d21ca7464705ca0264366d13dbbaa28a1166a
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_pipeline_qa_config test_land_config test_flow_config_schema test_flow_config_schema_drift test_skill_prose_diet -q, cd plugins/flow-next/tests && python3 -m unittest test_tracker_distribution -q, python3 scripts/gen_flow_config_schema.py --check, ./scripts/sync-codex.sh (twice, idempotent, no mirror diff), uvx ruff@0.16.0 check ., baseline: green (unittest 171 OK, schema check, ruff)
- PRs: