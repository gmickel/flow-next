---
satisfies: []  # historical: built the probe (removed in .4); evidence only
---

## Description

Pure-stdlib flowctl additions: `plan-sync-probe <task-id> --json` (deterministic drift-possibility probe, fail-open lattice), `planSync.gate` config key, and the gate ledger. No skill wiring here (fn-83.4).

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_plan_sync_probe.py` (new), `plugins/flow-next/tests/test_plansync_gate_config.py` (new)

## Approach

- **Touched-set (RANGE-BASED):** evidence via `load_task_with_state(id)["evidence"]` (runtime state — NOT task-md parsing; cmd_done write at flowctl.py:16476). Requires the new additive `evidence.base_commit` field (fn-83.4 makes the worker record it) — probe computes ONE range diff `git diff --no-renames --name-status <base_commit> <head>` (head = last evidence commit) for paths, and `git diff <base_commit> <head>` unified for hunk tokens (rc-checked subprocess, NO pipelines; renames appear as D+A so both paths count; interleaved foreign commits over-approximate — safe). **Missing `base_commit` / empty evidence / unresolvable range ⇒ decision `spawn`** (completeness proven or gate inapplicable). Multi-commit fix-loop tasks are the reason: per-commit enumeration of an incomplete list false-skips.
- **Hunk tokens:** from the base..head range unified diff; tokenize `+`/`-` lines; keep tokens passing the MORPHOLOGICAL identifier predicate (contains `_` | camelCase hump | dotted/`::`/`->` compound | ALL_CAPS≥2 | contains digit). Shape-based only — no stoplist.
- **Downstream reference extraction** (net-new): for each downstream todo task (current spec) AND — when `planSync.crossSpec` true (first deterministic reader of that key) — every open spec's BODY plus its todo tasks (plan-sync Phase 4b scans spec bodies too), parse body for path-shaped refs (`**Files:**` list items, `## Investigation targets` lines via the fn-79 fence-aware helpers `get_task_section`/`_iter_fence_aware` flowctl.py:5141/:5266, plus path-like tokens anywhere: backtick-tolerant, `:12-40`-suffix-tolerant). Match via `PurePosixPath`: exact, basename, directory-prefix (3.8-safe `.parts` tuple compare — `is_relative_to` is 3.9+). Token overlap: word-bounded search of kept hunk-tokens in downstream bodies.
- **Lattice (fail-open):** skip ⇔ no path overlap ∧ no token overlap ∧ deviation=="no" (passed in via `--deviation yes|no|missing` from the caller; missing⇒yes) ∧ clean run ∧ every scanned body (tasks; plus open spec bodies under crossSpec) yielded ≥1 parseable ref ∧ evidence present ∧ (crossSpec off ∨ enumeration succeeded). Else spawn. Output JSON per spec API contract (decision, facts{touched, overlaps[], tokens_matched[], deviation, unparseable_downstream[], cross_spec}, mode).
- **Config:** add `"gate": "on"` to the planSync block in `get_default_config()` (flowctl.py:1185); string-enum semantics per the pipeline.qa precedent (flowctl.py:1293; tests copy test_pipeline_qa_config.py shape — bool true NOT recognized).
- **Ledger:** `--record <mode>` appends the FIXED schema `{ts, spec, task, mode, decision, skip_index, audit_spawned, actual_drift: null, audit_miss: false, reason}` to `.flow/plansync-gate.jsonl` (atomic append via atomic_write pattern or O_APPEND single-write); `plan-sync-probe record-actual <task-id> --actual yes|no` updates the pending entry (or appends a paired record — implementer picks the simpler atomic shape and documents it).
- Argparse registration per the prospect subparser shape (flowctl.py:25991-26019).
- **Unit tests:** every lattice arm BOTH directions (each single condition flips skip→spawn), morphological predicate table-test, rename D+A both-paths, root-commit, Windows-path normalization, crossSpec enumeration failure ⇒ spawn, config enum defaults/rejects. tmp-repo fixtures per test_prospect_cli.py conventions (importlib load of flowctl.py, TemporaryDirectory + real git init). Test the PRODUCTION functions, not parallel constructions (memory: test-production-path).

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:1181-1340` (config defaults + materialization), `:5141-5300` (fence-aware section helpers), `:13851-13960` (export parsers), `:16362-16480` (cmd_done evidence), `:25991-26019` (prospect argparse shape)
- `plugins/flow-next/tests/test_pipeline_qa_config.py` (string-enum config test to copy), `test_prospect_cli.py` (tmp-repo + importlib conventions)
- `plugins/flow-next/agents/plan-sync.md:13-24` (input contract the probe's caller mirrors)

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:14845-15025` (export section assembly — fn-83.3's clone target; skim for shared helpers)

## Key context

Probe is pure read (no state mutation except the opt-in ledger). Determinism doctrine: audit counters/ledger are deterministic (no RNG). Python 3.8+ only, pure stdlib, Windows-safe (fn-77 discipline: PurePosixPath for git paths, os-native for filesystem).

## Acceptance

- [ ] Probe + config + ledger implemented per Approach; JSON shape matches the spec's API contract
- [ ] Unit tests: all lattice arms both ways (incl. missing-base ⇒ spawn and a multi-commit fix-loop fixture), predicate table, rename/Windows/crossSpec edges, config enum — green
- [ ] No pipelines in probe subprocess handling; rc-checked; nonzero exit on internal error
- [ ] Full pytest + smoke green; no version bump

## Done summary
Implemented `flowctl plan-sync-probe` — a pure-stdlib deterministic drift-possibility probe with the fn-83 fail-open lattice (range-based touched-set requiring `evidence.base_commit`, morphological hunk-token arm, PurePosixPath exact/basename/dir-prefix matching, parseable-refs + crossSpec arms), the `planSync.gate` string-enum config (off|shadow|on, default on), and the `.flow/plansync-gate.jsonl` gate ledger (O_APPEND fixed-schema records, deterministic 1-in-2/1-in-5 ramped audit slots, `record-actual` in-place pairing with audit_miss). 73 new unit tests cover every lattice arm both directions incl. multi-commit fix-loop, rename D+A, Windows paths, and the exact CLI wire form; full suite + smoke green; rp review SHIP first pass.
## Evidence
- Commits: 5993c44643f79c7ef21fdf700a1ac99b571a81bb
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (1468 tests, OK), python3 -m unittest discover -s plugins/flow-next/tests -p test_plan_sync_probe.py (57 tests), python3 -m unittest discover -s plugins/flow-next/tests -p test_plansync_gate_config.py (16 tests), bash plugins/flow-next/scripts/smoke_test.sh from non-repo cwd (138 passed)
- PRs: