---
satisfies: [R3, R10, R26, R30, R31, R33, R36]
---

## Description

Layer deprecation warnings and read-compatibility on top of T1's canonical surface. ALL `flowctl epic *` proxies (11 sub-subcommands) emit a one-line stderr warning per invocation (suppressible via `FLOW_NO_DEPRECATION=1`). All `--epic <id>` flag aliases on top-level subcommands emit the same warning. The `--section epic` value alias on `flowctl spec export-cognitive-aid` emits the same deprecation. Persisted JSON files write canonical `"spec":` only. CLI `--json` outputs dual-emit (canonical + legacy alias key) per R31 -- includes ALL keys: `spec`/`epic`, `specs`/`epics`, `spec_id`/`epic_id`. Read paths accept both forms. Read-path filesystem fallback. Ralph plumbing rename.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

- Add `_emit_rename_deprecation(legacy_form, canonical_form)` helper modeled on `_memory_emit_deprecation` at `flowctl.py:5655-5666`. Suppress via `FLOW_NO_DEPRECATION=1`.
- Wrap proxy registrations from T1 for ALL 11 sub-subcommands plus `flowctl epics`. Each invokes the helper before dispatching.
- `--epic <id>` flag aliases on ALL handlers: `task create`, `tasks`, `ready`, `validate`, `checkpoint save`, `checkpoint restore`. Each emits the warning.
- `--epics-file` -> `--specs-file` rename on `flowctl next`. Alias kept.
- `--section epic` value on `flowctl spec export-cognitive-aid` aliased to `--section spec` with stderr deprecation.
- **Persisted JSON write**: writes canonical `task["spec"] = ...` and `task.pop("epic", None)`. Same for `task["spec_id"] = ...` / `task.pop("epic_id", None)` if any field uses the `_id` suffix form. On-disk task JSON files contain only canonical names.
- **CLI `--json` output dual-emit (R31)**: command output assembly duplicates EVERY `epic`-named key into the legacy alias position. Apply at every site where `output["spec"] = ...` or `output["specs"] = ...` or `output["spec_id"] = ...` is written -- mirror to `output["epic"]` / `output["epics"]` / `output["epic_id"]`. The full list is determined at implementation time via `grep -n '"\(epic\|epic_id\|epics\)":' plugins/flow-next/scripts/flowctl.py` over output-construction sites. 2.0 drops the alias keys.
- **JSON read-compat**: at the ~15 read sites, replace `task.get("epic")` with `task.get("spec") or task.get("epic")`. Same for `epic_id` -> `task.get("spec_id") or task.get("epic_id")`. Same for `meta.get("next_epic")` -> `meta.get("next_spec") or meta.get("next_epic")`.
- Read-path filesystem fallback: helper `_resolve_spec_json_path(flow_dir, spec_id) -> Path`.
- Write-location helper from T1 finalized.
- Ralph plumbing: `EPICS_FILE` -> `SPECS_FILE`; `--epics-file` -> `--specs-file`. Alias deprecation on first read.
- **`flowctl next --json` reason-code compat**: emit BOTH `reason: "blocked_by_spec_deps"` AND `legacy_reason: "blocked_by_epic_deps"`.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:5655-5666` -- existing `_memory_emit_deprecation` pattern.
- `plugins/flow-next/scripts/flowctl.py:7256-7283` -- second instance.
- `plugins/flow-next/scripts/flowctl.py:5827-5870` -- `cmd_memory_add` legacy alias mapping.
- `plugins/flow-next/scripts/flowctl.py:18829, 19026, 18960` -- `--epic`/`--epics-file` flag handlers.
- `plugins/flow-next/scripts/flowctl.py:9897-9938, 12523-12545, 12656-12693, 18039-18041` -- handlers consuming `args.epic`.
- `plugins/flow-next/scripts/flowctl.py:11660` -- `cmd_epic_export_cognitive_aid` (T1 renamed; T2 adds `--section epic` value alias warning).
- All sites matching `grep -n '"\(epic\|epic_id\|epics\)":' plugins/flow-next/scripts/flowctl.py` -- write paths get dual-emit; read paths get fallback.
- Checkpoint subcommand parser.
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
- [ ] Read-path fallback: stage `.flow/epics/fn-X.json` and no `.flow/specs/fn-X.json` -- top-level `flowctl show fn-X` finds it via `_resolve_spec_json_path`.
- [ ] Write-location: on an unmigrated 0.x repo, `flowctl spec create --title "..."` writes to `.flow/epics/<id>.json`.
- [ ] Ralph: `EPICS_FILE=epics.txt flowctl next` works AND emits deprecation; `SPECS_FILE=epics.txt flowctl next` is silent.
- [ ] `meta.json` `next_epic` field read-compat: 0.x meta with only `next_epic` key reads correctly; new writes emit `next_spec` (T1 rule for fresh init; T3 migration handles existing meta).

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
