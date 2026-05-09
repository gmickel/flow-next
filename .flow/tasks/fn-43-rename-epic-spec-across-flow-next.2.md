---
satisfies: [R3, R10, R26, R30, R31, R33, R36]
---

## Description

Layer deprecation warnings and read-compatibility on top of T1's canonical surface. ALL `flowctl epic *` proxies (11 sub-subcommands) emit a one-line stderr warning per invocation (suppressible via `FLOW_NO_DEPRECATION=1`). All `--epic <id>` flag aliases on top-level subcommands emit the same warning. The `--section epic` value alias on `flowctl spec export-cognitive-aid` emits the same deprecation. Persisted JSON files write canonical `"spec":` only. CLI `--json` outputs dual-emit (canonical + legacy alias key) per R31 -- includes ALL keys: `spec`/`epic`, `specs`/`epics`, `spec_id`/`epic_id`. Read paths accept both forms. Read-path filesystem fallback. Ralph plumbing rename.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

- Add `_emit_rename_deprecation(legacy_form, canonical_form)` helper modeled on `_memory_emit_deprecation` at `flowctl.py:5655-5666`. Suppress via `FLOW_NO_DEPRECATION=1`.
- T1 landed parallel `p_spec` and `p_epic` subparsers via the shared `_add_spec_subparsers(parent_sub, noun=...)` helper at `flowctl.py:18960-19123`. Both subparsers `set_defaults(func=cmd_spec_*)` directly — there are no separate proxy wrappers; the `cmd_epic_*` symbols are Python module-level aliases pointing at the same `cmd_spec_*` function objects. T2 layers deprecation either by (a) wrapping the alias entries inside `_add_spec_subparsers` so the `epic` branch sets `func=` to a deprecation-emitting wrapper that calls the canonical handler, or (b) inspecting `args.command == "epic"` (or `args.epics_alias`) in `main()` and emitting before dispatch. Pick whichever keeps the dispatch cleaner. <!-- Updated by plan-sync: T1 used parallel-subparser registration not proxy wrappers -->
- `--epic <id>` flag aliases on ALL handlers: `task create`, `tasks`, `ready`, `validate`, `checkpoint save`, `checkpoint restore`. Each emits the warning.
- `--epics-file` -> `--specs-file` rename on `flowctl next`. Alias kept.
- `--section epic` value on `flowctl spec export-cognitive-aid` aliased to `--section spec` with stderr deprecation.
- **Persisted JSON write**: writes canonical `task["spec"] = ...` and `task.pop("epic", None)`. Same for `task["spec_id"] = ...` / `task.pop("epic_id", None)` if any field uses the `_id` suffix form. On-disk task JSON files contain only canonical names.
- **CLI `--json` output dual-emit (R31)**: command output assembly duplicates EVERY `epic`-named key into the legacy alias position. Apply at every site where `output["spec"] = ...` or `output["specs"] = ...` or `output["spec_id"] = ...` is written -- mirror to `output["epic"]` / `output["epics"]` / `output["epic_id"]`. The full list is determined at implementation time via `grep -n '"\(epic\|epic_id\|epics\)":' plugins/flow-next/scripts/flowctl.py` over output-construction sites. 2.0 drops the alias keys.
- **JSON read-compat**: at the ~15 read sites, replace `task.get("epic")` with `task.get("spec") or task.get("epic")`. Same for `epic_id` -> `task.get("spec_id") or task.get("epic_id")`. Same for `meta.get("next_epic")` -> `meta.get("next_spec") or meta.get("next_epic")`. T1 partially shipped read-compat in places (e.g. `cmd_tasks` already does `task_data.get("spec") or task_data.get("epic")`); T2 sweeps the remaining sites.
- Read-path filesystem fallback: T1 already shipped `find_spec_json_path(flow_dir, spec_id) -> Path` at `flowctl.py:3713-3732` (probes specs/ first, falls back to epics/). T2 verifies all read call-sites use it (no raw `flow_dir / EPICS_DIR / f"{id}.json"` constructions outside the helper). <!-- Updated by plan-sync: T1 shipped helper as find_spec_json_path not _resolve_spec_json_path -->
- Write-location helper from T1 finalized — `get_specs_json_write_dir(flow_dir)` at `flowctl.py:3692-3710`.
- Ralph plumbing: `EPICS_FILE` -> `SPECS_FILE`; `--epics-file` -> `--specs-file`. Alias deprecation on first read.
- **`flowctl next --json` reason-code compat**: emit BOTH `reason: "blocked_by_spec_deps"` AND `legacy_reason: "blocked_by_epic_deps"`.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py` -- existing `_memory_emit_deprecation` pattern (search for the function definition; T1's adds shifted line numbers — grep `def _memory_emit_deprecation`).
- `plugins/flow-next/scripts/flowctl.py` -- `cmd_memory_add` legacy alias mapping (grep `def cmd_memory_add`).
- `plugins/flow-next/scripts/flowctl.py` -- `--epic`/`--epics-file` flag handlers (grep `dest="epic"` and `--epics-file`; canonical `--spec` flags landed in T1's argparse block at `_add_spec_subparsers` and `p_validate` / `p_checkpoint_*` / `p_task_create`).
- `plugins/flow-next/scripts/flowctl.py` -- handlers consuming `args.epic` (grep `args.epic` / `getattr(args, "epic"`); T1 added `resolve_spec_arg(args)` at `flowctl.py:3735-3744` which centralizes this — T2 makes sure call sites use it).
- `plugins/flow-next/scripts/flowctl.py` -- `cmd_spec_export_cognitive_aid` is canonical (T1 rename); `cmd_epic_export_cognitive_aid` is the Python module-level alias at `flowctl.py:12219`. T2 adds the `--section epic` value alias warning (T1 already accepts both silently in `EXPORT_COGNITIVE_AID_SECTIONS` at `flowctl.py:10840-10851`). <!-- Updated by plan-sync: T1 renamed function; line numbers shifted -->
- All sites matching `grep -n '"\(epic\|epic_id\|epics\)":' plugins/flow-next/scripts/flowctl.py` -- write paths get dual-emit; read paths get fallback. T1 already shipped dual-emit for `cmd_specs` (`specs`/`epics`), `cmd_validate` (`spec`/`epic` + `specs`/`epics`), `cmd_tasks` (`spec`/`epic` per-task), and `cmd_spec_export_cognitive_aid` payload top-level (`spec`/`epic`). T2 sweeps remaining sites.
- Checkpoint subcommand parser at `flowctl.py:19402-19440` (canonical `--spec` + alias `--epic` registered in T1).
- `cmd_next` reason-code emission paths.

## Key context

- `FLOW_NO_DEPRECATION=1` is the existing convention.
- Stderr emission must NOT pollute `--json` stdout.
- **On-disk vs CLI-output split**: persisted JSON has canonical names only. CLI `--json` output dual-emits both forms.
- Three categories of dual-emit: object keys (`spec`/`epic`), array keys (`specs`/`epics`), id keys (`spec_id`/`epic_id`). All three are R31 surface.

## Acceptance

- [ ] All 11 `flowctl epic *` sub-subcommands print stderr deprecation; `FLOW_NO_DEPRECATION=1` suppresses.
- [ ] `flowctl epic create --title "Test" --json | jq .id` parses cleanly.
- [ ] All `--epic <id>` flag uses (`task create`, `tasks`, `ready`, `validate`, `checkpoint save`, `checkpoint restore`) work AND emit deprecation; `--spec <id>` is silent.
- [ ] `flowctl spec export-cognitive-aid <id> --section epic --json` succeeds AND emits deprecation; `--section spec` is silent.
- [ ] `flowctl next --epics-file /tmp/x` works AND emits deprecation; `--specs-file /tmp/x` is silent.
- [ ] **Persisted task JSON file contains canonical names only** -- `"spec":` not `"epic":`; `"spec_id":` not `"epic_id":` (where applicable). Reading a 0.x task JSON (with legacy field names) succeeds.
- [ ] **CLI `--json` output dual-emits all R31 key categories**: `flowctl tasks --json` returns each task with both `"spec":` and `"epic":` (same value); `flowctl specs --json` returns both `"specs":` and `"epics":` (same array); any `--json` output containing `"spec_id":` also contains `"epic_id":` (same value).
- [ ] **`flowctl next --json` reason-code dual-emit**: `{"reason": "blocked_by_spec_deps", "legacy_reason": "blocked_by_epic_deps", ...}` through 1.x.
- [ ] Read-path fallback: stage `.flow/epics/fn-X.json` and no `.flow/specs/fn-X.json` -- top-level `flowctl show fn-X` finds it via `find_spec_json_path`.
- [ ] Write-location: on an unmigrated 0.x repo, `flowctl spec create --title "..."` writes to `.flow/epics/<id>.json`.
- [ ] Ralph: `EPICS_FILE=epics.txt flowctl next` works AND emits deprecation; `SPECS_FILE=epics.txt flowctl next` is silent.
- [ ] `meta.json` `next_epic` field read-compat: 0.x meta with only `next_epic` key reads correctly; new writes emit `next_spec` (T1 rule for fresh init; T3 migration handles existing meta).

## Done summary
Layered the deprecation/alias surface on T1's parallel-subparser scaffolding: one-shot stderr deprecations on every legacy epic-named user-facing entry point (flowctl epic *, flowctl epics, --epic, --epics-file, EPICS_FILE, --section epic), persisted task JSON canonicalized to 'spec' only via a new canonicalize_task_for_write helper applied at every write site, normalize_task migrates legacy 0.x epic->spec on read, R31 dual-emit (spec/epic, specs/epics, spec_id/epic_id, plus reason: blocked_by_spec_deps + legacy_reason: blocked_by_epic_deps) extended to all remaining CLI --json outputs, and checkpoint files write canonical with read-compat for 0.x-saved checkpoints.
## Evidence
- Commits: 3658890c5d6b8b4b3c9a3d4ea05e5a2afe69caa0, 6b2175bc98c8fe28e40d6a1cb13f7c329b514dc5
- Tests: python3 -c 'import ast; ast.parse(open("plugins/flow-next/scripts/flowctl.py").read())', manual smoke: flowctl init/spec create/task create/dep add/checkpoint save+restore/spec set-title/spec close — all canonical writes verified, verified --epic / --epics-file / --section epic / EPICS_FILE / flowctl epic / flowctl epics deprecations fire, all canonical forms silent, verified flowctl next blocked-deps emits reason: blocked_by_spec_deps + legacy_reason: blocked_by_epic_deps + blocked_specs + blocked_epics, verified legacy 0.x task JSON ("epic" key only) reads correctly via normalize_task; canonicalizes in-place on first write via canonicalize_task_for_write, verified read-path filesystem fallback (epics/<id>.json + specs/<id>.md only) works on flowctl show, verified meta.json with only next_epic key still passes flowctl detect, verified strategy_smoke_test.sh + glossary_smoke_test.sh + audit_smoke_test.sh still pass, codex:gpt-5.5:high impl-review SHIP after one NEEDS_WORK → SHIP cycle
- PRs: