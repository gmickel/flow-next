---
satisfies: [R2]
---
# fn-166-flowctl-module-split-importable.3 Extract review-terminal machinery into flowctl_review/ package

## Description
Extract the fn-159 review-terminal machinery out of flowctl.py into a new `flowctl_review/` package next to `flowctl_tracker/`, moving code verbatim with zero behavior change. The cross-boundary interface is DECIDED: explicit injection + facade re-export (below). Manual propagation only — the manifest/integrity contract is task .4.

**Size:** M/L (one cohesive mechanical move — do NOT split further; a partial move is a broken intermediate state)
**Files:** `plugins/flow-next/scripts/flowctl.py` (region removed, wiring + facade re-exports added), NEW `plugins/flow-next/scripts/flowctl_review/` package, `.flow/bin/flowctl.py` + `.flow/bin/flowctl_review/` (propagation)

### Approach
- **Boundary is defined by SYMBOLS, not line numbers** (line refs are orientation; re-grep at implementation time): from `get_max_review_iterations` (~:9546) through the COMPLETE `build_convergence_ratchet_block` function (def ~:11797, body ends ~:11901). `build_rereview_preamble` (~:11904) explicitly STAYS in flowctl.py. Prompt-template loaders + pinned constants (~:9425-9489) and `build_review_prompt` STAY in flowctl.py — `test_prompt_text_pinned` needs zero changes (if a pinned constant must move, change only the test read path; hashes identical).
- **Cross-boundary interface (decided, review round 1):** the package NEVER imports flowctl by name — under direct `python3 flowctl.py` the host module is `__main__`, so `import flowctl` would execute a SECOND module instance with separate lock/cache singletons (silent split-brain). Instead flowctl.py passes its own module object (or a narrow context object of the needed callables) into the package at wiring time (explicit injection). flowctl.py keeps facade re-exports binding every extracted symbol name so the dozens of downstream flowctl.py call sites stay verbatim.
- **Mechanical cross-boundary symbol inventory BEFORE moving:** run an AST/pyflakes pass over the region to enumerate (a) every flowctl-owned name the region references — the seven known helpers (`atomic_write_json`, `now_iso`, `get_flow_dir`, `find_spec_json_path`, `load_json_or_exit`, `normalize_epic`, `CrossProcessLockError`) are a STARTING list, not the full set (the region also reaches e.g. `_completion_review_receipt_recovery_path` ~:39672, receipt locking/preservation, findings validation, criteria parsing) — and (b) every extracted name that later flowctl.py code consumes (these need facade re-exports). Record both lists in the task summary.
- Package load in flowctl.py: flowctl_tracker-style lazy `sys.path.insert` guard + soft-fail message naming `flowctl_review` (patterns at `flowctl.py:1706-1709`, `:38576-38582`). Absent package → actionable message, never a bare traceback.
- **Runtime coverage of all three load identities:** imported `flowctl` (task .2's launcher path), direct `python3 flowctl.py`, and the bootstrap static path — a review command must succeed identically through each; add/extend a test if no suite exercises them.
- flowctl.py must NEVER contain the literal string "MANIFEST.json" (`test_no_per_command_hashing`) — no manifest logic in flowctl.py.
- Resist improving code while moving — verbatim moves only (incl. comments; the `_REVIEW_REPLAY_PRECEDENCE` ordering comment ~:10948-10952 is load-bearing: MAJOR_RETHINK outranks NEEDS_WORK).
- Module-level lock/cache singletons keep exactly ONE home (the package), reached via injection/facade — never duplicated.
- Propagate: `cp` flowctl.py; `rsync -a --delete --exclude __pycache__ plugins/flow-next/scripts/flowctl_review/ .flow/bin/flowctl_review/`; `python3 scripts/gen_tracker_manifest.py` (re-hash of the changed flowctl.py).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:9425-11910` — the region (symbol boundaries above; re-grep line refs)
- `plugins/flow-next/scripts/flowctl.py:1706-1709` and `:38576-38582` — flowctl_tracker lazy-import + soft-fail pattern to mirror
- `plugins/flow-next/scripts/flowctl_tracker/` — package layout template

**Optional** (reference as needed):
- `plugins/flow-next/tests/test_prompt_text_pinned.py:60-90` — pin mechanics (goal: zero changes needed)
- `plugins/flow-next/tests/test_review_convergence_cap.py` — heaviest consumer suite

### Key context
- fn-159 built this region with explicit function boundaries — the seam is clean, but the dependency surface is wider than it looks: inventory first, move second.
- Memory lessons: test production `cmd_*` paths, not parallel constructions; fn-141 adjacent-fidelity sweeps (check every semantic claim adjacent to moved code).
## Acceptance
- [ ] Review-terminal region (symbol-defined: `get_max_review_iterations` through complete `build_convergence_ratchet_block`; `build_rereview_preamble` stays) lives in `flowctl_review/`; flowctl.py shrinks accordingly
- [ ] Mechanical cross-boundary symbol inventory recorded (both directions) BEFORE the move; injection context covers every inbound name; facade re-exports cover every outbound name
- [ ] Package never imports flowctl by name; a review command succeeds identically through all three load identities (imported flowctl, `python3 flowctl.py`, bootstrap) — test-covered
- [ ] Absent-package soft-fail names flowctl_review with an actionable message (no bare traceback); lock/cache singletons have exactly one home
- [ ] `test_prompt_text_pinned` green with UNCHANGED hashes; `test_review_prompt_template_parity` green
- [ ] Focused suites green: all `test_review_*` suites + `test_flowctl_surface` + `test_tracker_distribution` + `test_host_review_backend`
- [ ] Propagation done (cp flowctl.py + rsync flowctl_review + gen_tracker_manifest.py); flowctl.py contains no "MANIFEST.json" literal
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
