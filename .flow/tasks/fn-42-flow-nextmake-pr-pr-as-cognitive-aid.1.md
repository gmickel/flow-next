---
satisfies: [R4, R5, R6]
---

## Description

Build the deterministic Python plumbing that aggregates nine input streams (epic spec, tasks, decisions/bug/architecture-patterns memory, glossary diff, strategy alignment, diff stats, review receipts) into one structured JSON payload the skill consumes. Single subcommand: `flowctl epic export-cognitive-aid <epic-id> --base <ref> [--section <name>] [--json]`.

**Size:** M (one file, substantial new function ~300+ LOC, but isolated)
**Files:** `plugins/flow-next/scripts/flowctl.py`

This is the early proof point: if the aggregator can't be cleanly assembled from existing helpers, re-evaluate before building the skill on top.

## Approach

- **Function placement:** drop `cmd_epic_export_cognitive_aid` between `cmd_epic_set_backend` and the next non-epic function (currently around `flowctl.py:10533+`). Function naming convention is `cmd_<noun>_<verb>` for grouped subcommands — verified across `cmd_epic_create`, `cmd_prospect_read`, `cmd_strategy_read`.
- **Argparse subparser:** add to `epic_sub` cluster around `flowctl.py:17404` (right after `p_epic_set_backend`). Use existing pattern: `epic_sub.add_parser("export-cognitive-aid", help="...")`. `--base` required, `--section` optional with `choices=["epic","tasks","memory","glossary","strategy","diff","reviews"]`, `--json` action_true.
- **Output convention:** `json_output(payload)` for `--json`, human-readable summary for non-JSON. `error_exit(msg, use_json=args.json, code=N)` — exit 1 generic, 2 invalid args, 3 corrupt artifact.
- **Reuse helpers (subprocess-callable from skills, importable from cmd):**
  - `is_epic_id(id)`, `flow_dir / EPICS_DIR / f"{id}.json"`, `load_json_or_exit`, `normalize_epic` for epic load
  - `load_task_with_state(task_id)` for per-task load with merged runtime (`done_summary`, `evidence`)
  - `_memory_iter_entries(memory_dir, track=..., category=...)` at `flowctl.py:6099` for memory aggregation
  - `find_strategy_file(start)` + `_strategy_load(path)` at `flowctl.py:504, 9225`
  - `find_all_glossaries(start)` + `parse_glossary_file(text)` at `flowctl.py:254, 325`
  - `atomic_write` for any file output
- **Glossary diff vs base** (no existing helper — write inline in this function):
  - `head_text = path.read_text()`
  - `base_text = subprocess.run(["git","show",f"{base}:{rel_path}"], ...).stdout`
  - Parse both via `parse_glossary_file`; diff by term name → `{added, removed, renamed}` (renamed = heuristic on definition similarity if 2026-Q2 stretch goal; v1 just `added`/`removed`)
- **Diff stats:** `git diff --numstat -M --diff-filter=AMRD <merge-base>..HEAD` for per-file additions/deletions. `git diff --shortstat -M` for header. `git diff --name-status -M` for status (A/M/R/D). Use `-M` so renames don't double-count churn (rename detection on by default but explicit is safer).
- **`merge_base`:** `git merge-base <base> HEAD` — returns sha. If `<base>` invalid, error exit 1 with hint to pass valid `--base`.
- **`cross_module_changes` derivation:** parse first 2 path components per file (`plugins/flow-next` vs `scripts`). Detect new combinations across the diff. Plus heuristic: grep `^[+]\s*(import|from|require|use)` in the unified diff to detect new dependency edges.
- **`public_exports_changed` derivation:** for each `index.{ts,js,py,mjs}` / `__init__.py` / `lib/*` / `mod.rs` file in the diff, parse added/removed `(export|def|class|fn pub)` lines. Crude but catches the high-signal cases.
- **`security_sensitive_paths`:** match against a hardcoded list — `auth/`, `crypto/`, `.github/workflows/`, `scripts/hooks/`, `*.pem`, filenames containing `secret|token|credential|key`. List goes in a module-level constant (e.g. `SECURITY_SENSITIVE_PATTERNS`).
- **`high_churn_files`:** sort `files[]` by `additions+deletions` descending, top 5.
- **Graceful degradation (informed by epic-scout's R30 suggestion):** every optional input stream returns `[]` or empty struct when absent. Missing `STRATEGY.md` → `strategy_alignment: {tracks_served: [], drift_flagged: []}`. No memory entries → empty arrays. No deferred findings → empty array. No `gh` PR open → omit (caller checks). Never raise on absence.
- **`--section` filter:** trim payload to one slice keyed by section name. Used for debugging and downstream skills that want only one slice.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:8391-8515` — `cmd_prospect_read` (closest analog: id resolution, --section filter, --json mode, corrupt-state exit code)
- `plugins/flow-next/scripts/flowctl.py:9324-9392` — `cmd_strategy_read` (file-not-found handling, --section filter)
- `plugins/flow-next/scripts/flowctl.py:9456-10538` — `cmd_epic_*` cluster (placement reference)
- `plugins/flow-next/scripts/flowctl.py:17317-17404` — argparse subparser registration block for epic
- `plugins/flow-next/scripts/flowctl.py:6099` — `_memory_iter_entries` (memory aggregation pattern)
- `plugins/flow-next/scripts/flowctl.py:254-440` — glossary helpers (`find_all_glossaries`, `parse_glossary_file`, `render_glossary_file`)

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl.py:504, 9225` — strategy helpers (`find_strategy_file`, `_strategy_load`)
- `plugins/flow-next/scripts/flowctl.py:9742-9755` — `cmd_show` (epic JSON load + normalize)

## Acceptance

- [ ] `flowctl epic export-cognitive-aid <epic-id> --base <ref> --json` returns valid JSON matching the schema in the epic spec's Architecture & Data Models section: top-level keys `epic`, `tasks`, `tasks_summary`, `memory_during_epic`, `glossary_changes`, `strategy_alignment`, `diff_summary`, `review_receipts`, `deferred_findings`.
- [ ] `--section <name>` filter (one of `epic|tasks|memory|glossary|strategy|diff|reviews`) returns only that slice; without `--section` returns the full payload.
- [ ] Exits 1 on missing epic, 2 on invalid args (e.g. unrecognized `--section`), 3 on corrupt epic JSON. Honors `--json` for error output.
- [ ] Graceful degradation: missing `STRATEGY.md` → `strategy_alignment.tracks_served: []`; no decisions/bug/architecture-patterns memory → empty arrays; no glossary → empty diffs; no review receipts → `review_receipts: []`. Never crashes on absent optional input.
- [ ] `diff_summary.files[]` populated from `git diff --numstat -M --diff-filter=AMRD <merge-base>..HEAD`. `merge_base_sha` field set. `modules_touched`, `cross_module_changes`, `public_exports_changed`, `security_sensitive_paths`, `high_churn_files` populated.
- [ ] `tasks_summary.uncovered_r_ids[]` lists every R-ID in spec acceptance criteria that no `done` task's `satisfies` covers.
- [ ] No regressions in existing flowctl smoke (`ci_test.sh`, `prospect_smoke_test.sh`, etc.).

## Done summary

_(populated by /flow-next:work after task completes)_

## Evidence

_(populated by /flow-next:work after task completes)_
