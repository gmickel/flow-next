---
satisfies: [R7, R8, R9, R10]
---

## Description

Sweep the smaller uncached repeat offenders found by fn-101, batch the cognitive-aid export's git-grep fan-out, and land the CHANGELOG/docs notes. No behavior change anywhere; every quantitative claim gets its own test.

**Size:** M
**Files:** plugins/flow-next/scripts/flowctl.py, .flow/bin/flowctl.py (mirror, same commit), plugins/flow-next/tests/test_hot_path_sweep.py (new), plugins/flow-next/tests/test_export_traceability.py (extend), CHANGELOG.md, plugins/flow-next/docs/flowctl.md

## Approach

- `get_cursor_version` (flowctl.py:4737) / `get_copilot_version` (:4525): per-process memo dict caching SUCCESSFUL probes only, keyed by `shutil.which()`-resolved executable path (transient CLI failure never sticky; PATH change re-probes because the key changes). Do NOT touch the disk model cache (:3249).
- Prospect: fold the triple read+frontmatter-parse per artifact to ONE read passed down (`_prospect_iter_artifacts._emit` :11035 consuming what `_prospect_detect_corruption` :8194 / `_prospect_artifact_status` :8267 already read); `_prospect_resolve_id` (:11133) returns the single descriptor on an exact filename hit instead of scanning the dir.
- Config: VERIFIED no-op for current state (`_CONFIG_KEY_ALIASES = {}` - live path already parses once; dormant alias machinery is fn-111 territory). No config edits in this task.
- `cmd_tasks` (:14029/:14032): second `get_flow_dir()` absorbed by task .1's cache - verify only.
- `_export_removed_export_refs` (:16034): one `git grep -n -e s1 --or -e s2 ...` (chunk at ~20 symbols per call) replacing up to 40 sequential calls. Per-symbol attribution is recovered by post-filtering the batched output in Python: for each returned line, attribute it to EVERY symbol whose existing match semantics hit that line (preserve current word/substring semantics exactly - read the current per-symbol grep invocation first and replicate); deterministic symbol iteration order; per-symbol reference cap unchanged.
- CHANGELOG `## Unreleased` entry (bold-lead bullet naming fn-109, mechanism sub-bullets, closing "No version bump (batched releases)."). docs/flowctl.md: one-line perf note under `### list` and `### status`.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:16020-16060` - CURRENT per-symbol git grep semantics (flags, pattern shape, cap) - replicate exactly in the batch
- `plugins/flow-next/scripts/flowctl.py:4500-4800` - version getters + call sites
- `plugins/flow-next/scripts/flowctl.py:8194-8300,11035-11160` - prospect read paths
- `plugins/flow-next/tests/test_export_traceability.py` - existing export test shape to extend

**Optional:**
- `plugins/flow-next/tests/test_prospect_artifact.py`, `test_prospect_cli.py` - suites that must pass unmodified
- `plugins/flow-next/tests/test_backend_spec.py:1011-1051` - subprocess mock/restore precedent

## Key context

- Overlap warning: fn-111 (config alias removal + export flags) and fn-112/fn-115 (BACKEND_REGISTRY region) land AFTER fn-109 - keep edits minimal and mechanical.
- Review round 1 findings baked in: success-only + executable-path-keyed version cache; config item dropped (dormant-only); every count claim needs a test.

## Acceptance

- [ ] Version getters: one successful version subprocess per resolved executable per process; tests for repeat-success (1 spawn), failure-then-success (2 spawns, no sticky failure), and PATH-change re-probe (R7)
- [ ] Prospect: read-count test asserts the descriptor-construction path (`_prospect_iter_artifacts` + corruption/status probes) opens+parses each artifact exactly once per enumeration (was 3); consumer reads outside enumeration unchanged; prospect suites pass unmodified (R7)
- [ ] Export batching: 40 removed symbols -> <=2 git grep subprocess calls (count test); multi-symbol single line attributed to both; prefix-collision case (foo vs foobar) preserves current semantics; per-symbol cap preserved; export payload byte-identical vs pre-change on a fixture spec (R8)
- [ ] CHANGELOG Unreleased entry + docs/flowctl.md perf note landed (R10)
- [ ] Dual-copy parity + full unittest + smoke_test.sh (from temp dir, absolute path) green (R9)

## Done summary
Swept the fn-101 uncached repeat offenders: success-only executable-path-keyed memo for get_copilot_version/get_cursor_version, prospect descriptor construction folded to one read+parse per artifact (with an exact-hit _prospect_resolve_id shortcut preserving walk-filter and separator-id parity), and _export_removed_export_refs batched to <=2 git grep calls for 40 symbols (--color=never, per-symbol word-boundary attribution, oracle-tested byte parity). CHANGELOG Unreleased entry + docs/flowctl.md perf notes landed; codex review NEEDS_WORK (forced-color SGR dropped refs) fixed -> SHIP.
## Evidence
- Commits: 90e3de47e8e00ab155d8f4f039ee4ffac306def7, 17f3c3c3ab2086eb6cc4ae2fdcf8094a912679a1
- Tests: baseline: green (fn-109.1 gates green at base commit 0b88b4d7), python3 -m unittest discover -s plugins/flow-next/tests -q (1858 tests OK, skipped=2), (cd "$(mktemp -d)" && bash plugins/flow-next/scripts/smoke_test.sh) (144 passed, 0 failed), python3 -m unittest discover -s plugins/flow-next/tests -p test_hot_path_sweep.py (11 OK), python3 -m unittest discover -s plugins/flow-next/tests -p test_export_traceability.py (31 OK), cmp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py (byte parity), time .flow/bin/flowctl list --json (0.52s) / status (0.41s)
- PRs: