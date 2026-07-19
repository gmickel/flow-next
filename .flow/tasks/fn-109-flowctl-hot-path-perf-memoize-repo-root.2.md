---
satisfies: [R7, R8, R9, R10]
---

## Description

Sweep the smaller uncached repeat offenders found by fn-101, batch the cognitive-aid export's git-grep fan-out, and land the CHANGELOG/docs notes. No behavior change anywhere.

**Size:** M
**Files:** plugins/flow-next/scripts/flowctl.py, .flow/bin/flowctl.py (mirror, same commit), CHANGELOG.md, plugins/flow-next/docs/flowctl.md

## Approach

- `get_cursor_version` (flowctl.py:4737) / `get_copilot_version` (:4525): per-process memo dict. Do NOT touch the disk model cache (:3249) - out of scope.
- Prospect: fold the triple read+frontmatter-parse per artifact to ONE read passed down (`_prospect_iter_artifacts._emit` :11035 consuming what `_prospect_detect_corruption` :8194 / `_prospect_artifact_status` :8267 already read); `_prospect_resolve_id` (:11133) returns the single descriptor on an exact filename hit instead of scanning the dir.
- Config: `cmd_config_get` + `resolve_config_key_for_read` (:1435, :7203) parse config.json ONCE per invocation and pass the parsed dict down.
- `cmd_tasks` (:14029/:14032): second `get_flow_dir()` absorbed by task .1's cache - verify, no code needed unless a literal dup remains.
- `_export_removed_export_refs` (:16034): one `git grep -n -e s1 --or -e s2 ...` (chunk at ~20 symbols per call for argv safety) replacing up to 40 sequential calls; output parsing preserves existing per-symbol attribution.
- CHANGELOG `## Unreleased` entry per repo convention (bold-lead bullet naming fn-109, mechanism sub-bullets, closing "No version bump (batched releases)."). docs/flowctl.md: one-line perf note under `### list` and `### status`.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:8194-8300,11035-11160` - prospect read paths
- `plugins/flow-next/scripts/flowctl.py:1435-1510,7203-7260` - config resolver + inline dup
- `plugins/flow-next/scripts/flowctl.py:16020-16060` - export git-grep fan-out
- `CHANGELOG.md:1-40` - Unreleased entry format (match the fn-97-era shape)

**Optional:**
- `plugins/flow-next/tests/test_prospect_artifact.py`, `test_prospect_cli.py` - suites that must pass unmodified
- `plugins/flow-next/tests/test_export_traceability.py` - export byte-parity anchor

## Key context

- Overlap warning: fn-111 (config alias removal + export flags) and fn-112/fn-115 (BACKEND_REGISTRY region) touch adjacent lines and land AFTER fn-109 - keep these edits minimal and mechanical so their rebases stay trivial.
- Export byte-parity matters: make-pr/qa consume the export; R8 requires identical output on a fixture spec.

## Acceptance

- [ ] Version getters called once per process under repeat dispatch paths; prospect artifacts read+parsed exactly once per item; config.json parsed once per `config get` (R7)
- [ ] Existing prospect/config/backend suites pass UNMODIFIED (R7)
- [ ] Export of a spec with 40 removed symbols issues <= 2 git grep calls; export output byte-identical to pre-change on a fixture (R8)
- [ ] CHANGELOG Unreleased entry + docs/flowctl.md perf note landed (R10)
- [ ] Dual-copy parity + full unittest + smoke_test.sh green (R9)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
