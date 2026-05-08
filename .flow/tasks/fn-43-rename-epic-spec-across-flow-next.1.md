---
satisfies: [R1, R2, R4, R26, R31]
---

## Description

Add canonical `flowctl spec *` subcommands as primary verbs; rename internal Python identifiers (functions, classes, constants, helpers, ID logic). Keep `flowctl epic *` functional via thin proxy registration that dispatches to the same `cmd_spec_*` handlers. Both `--section spec` and `--section epic` are accepted by the cognitive-aid export argparse silently in T1; T2 layers the deprecation emission. Fresh `flowctl init` writes `.flow/meta.json` with `schema_version: 3` and `next_spec` (NOT `next_epic`). T3 covers migration of existing 0.x meta.json files. NO migration logic yet (T3). NO banner yet (T4).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

- Rename ALL 11 sub-subcommands of `flowctl epic` plus the top-level `flowctl epics`. The 12 underlying `cmd_epic_*` functions per repo-scout: `cmd_epic_create`, `cmd_epics`, `cmd_epic_set_plan`, `cmd_epic_set_plan_review_status`, `cmd_epic_set_completion_review_status`, `cmd_epic_set_branch`, `cmd_epic_set_title`, `cmd_epic_add_dep`, `cmd_epic_rm_dep`, `cmd_epic_set_backend`, `cmd_epic_export_cognitive_aid`, `cmd_epic_close`. Top-level `flowctl show` is NOT renamed.
- Rename module-level constants: `EPICS_DIR = "epics"` -> `SPECS_JSON_DIR = "specs"`; `EPIC_STATUS` -> `SPEC_STATUS`. Bump `SCHEMA_VERSION = 2` -> `3` AND extend `SUPPORTED_SCHEMA_VERSIONS` to include 3 (T3 adds 3 to migrated files; T1 ships fresh files at 3).
- Rename helpers + all callsites: `is_epic_id` -> `is_spec_id`; `epic_id_from_task` -> `spec_id_from_task`; `scan_max_epic_id` -> `scan_max_spec_id`.
- Argparse: register `p_spec` with the full 11-subcommand block as primary; keep `p_epic` registration as alias dispatching to the same `cmd_spec_*` handlers via shared `set_defaults(func=...)`. **No deprecation emitter wrapper yet (T2 adds it).** Both verb forms work silently.
- Add `flowctl specs` parser; keep `flowctl epics` as alias.
- Cognitive-aid export: argparse `choices=` for `--section` accepts BOTH `spec` (canonical) and `epic` (alias) silently. Both succeed; both produce identical payloads. T2 adds the deprecation warning.
- **Fresh `flowctl init` writes `.flow/meta.json` containing `{"schema_version": 3, "next_spec": 1}`** -- NOT `next_epic`. (T3 covers the migration path that updates an existing 0.x meta.json.)
- Write-location rule: `flowctl init` post-1.0 writes `.flow/specs/`; existing 0.x layouts (no sentinel + `.flow/epics/` exists) keep writing to `.flow/epics/`; sentinel-present writes go to `.flow/specs/`.
- Cognitive-aid export (R31): `EXPORT_COGNITIVE_AID_SECTIONS["spec"]` as primary; payload top-level key renamed to `"spec"`. T7a coordinates make-pr workflow prose.
- `flowctl specs --json` payload (R31): canonical top-level key is `"specs":`; emit ALSO `"epics":` (same array, alias key) through 1.x.
- Internal Python rename does NOT include checkpoint schema per spec Boundaries.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:54-57` -- module constants block.
- `plugins/flow-next/scripts/flowctl.py:1650, 3634` -- ID helpers.
- `plugins/flow-next/scripts/flowctl.py:18706-18823, 18927` -- argparse subparser block.
- `plugins/flow-next/scripts/flowctl.py:10626-10645, 11816, 11927` -- cognitive-aid export sections + payload keys.
- `plugins/flow-next/scripts/flowctl.py:9822` -- `cmd_epics` payload structure.
- `plugins/flow-next/scripts/flowctl.py:50` -- `SCHEMA_VERSION = 2`. Bump to 3.
- `plugins/flow-next/scripts/flowctl.py:3972` -- `meta = {"schema_version": SCHEMA_VERSION, "next_epic": 1}` init point. Rewrite to use `next_spec` field name.
- Locate `SUPPORTED_SCHEMA_VERSIONS` (existing constant; add 3).

## Key context

- T1 silently accepts both verb forms and both `--section` values. T2 layers deprecation emissions.
- Top-level `flowctl show` is NOT renamed.
- Two version markers: `meta.json["schema_version"] == 3` AND `.flow/.flow_version == "1.0.0"`. T1 writes the schema_version on fresh init; T3's migration handles existing repos AND writes the .flow_version sentinel.

## Acceptance

- [ ] All 11 canonical `flowctl spec *` sub-subcommands exist and behave identically to their `flowctl epic *` predecessors.
- [ ] `flowctl specs --json` returns `{"success": true, "specs": [...], "epics": [...]}` -- both keys reference the same array.
- [ ] `flowctl epics --json` produces identical output (proxy).
- [ ] `flowctl spec export-cognitive-aid <id> --json` returns payload with top-level `"spec":` key (R31).
- [ ] `flowctl spec export-cognitive-aid <id> --section spec --json` and `--section epic --json` both succeed silently in T1 (T2 adds the warning to `--section epic`).
- [ ] **Fresh `flowctl init` writes `.flow/meta.json` containing `schema_version: 3` AND `next_spec` (NOT `next_epic`).** No `.flow/epics/` directory created.
- [ ] On an existing 0.x `.flow/`, `flowctl spec create --title "..."` writes to `.flow/epics/<id>.json` (alias-mode promise preserved).
- [ ] Reading a 0.x `.flow/meta.json` (with only `next_epic` key) succeeds via T2's read-compat helper.
- [ ] Top-level `flowctl show fn-X` resolves the spec; NOT renamed and NOT shadowed.
- [ ] All 12+ callsites of renamed helpers updated.
- [ ] Existing smoke tests pass without modification.
- [ ] Checkpoint JSON schema unchanged per spec Boundaries.

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
