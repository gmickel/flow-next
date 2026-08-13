---
satisfies: [R1, R2]
---
# fn-191-flowctl-review-terminal-machinery.1 Cross-boundary symbol inventory + extract the region into the package with injected context

## Description
Move the review-terminal region into its own package next to the tracker package, wired by explicit injection so the package never imports the host by name. The inventory of what the moved code reaches is DERIVED mechanically first - a hand-written helper list is how a missing symbol becomes a runtime failure in a rarely-taken branch.

**Size:** M/L (if the inventory shows the region cannot move without dragging a pinned prompt constant, split rather than stretch)
**Files:** NEW package dir beside `plugins/flow-next/scripts/flowctl_tracker/` (implementer names it, e.g. `plugins/flow-next/scripts/flowctl_review/`); `plugins/flow-next/scripts/flowctl.py` (region removed, facade re-exports + lazy load guard added)
**Touches:** [plugins/flow-next/scripts/flowctl.py, plugins/flow-next/scripts/flowctl_review/**]

### Approach
- **Boundary is the symbol list, re-derived at implementation time.** Reference derivation 2026-08-13 on main @ 9e111db4: region runs from `get_max_review_iterations` (~:9912) through the COMPLETE `build_convergence_ratchet_block` function (def ~:12420, body ends ~:12544) - about 2,633 lines. `build_rereview_preamble` (~:12545) STAYS. The prompt-template loaders and `build_review_prompt` STAY, so no pinned prompt constant moves and `test_prompt_text_pinned` needs no edit. These coordinates drifted 366 lines in nine days - grep the symbols, never trust the numbers.
- **Mechanical inventory before the move:** run an AST or linter pass over the moved region to list every name it resolves outside itself. The obvious helpers (atomic JSON write, timestamp, flow-dir resolution, spec-json lookup, load-or-exit, epic normalization, the cross-process lock error) are a STARTING list only - the region also reaches receipt-recovery paths, receipt locking/preservation, findings validation, and criteria parsing. Record the derived list in the task summary.
- **Wiring direction is one-way and injected.** Host loads the package behind the lazy `sys.path` guard + soft-fail message pattern the tracker package already uses. The package NEVER does `import flowctl`: under direct script invocation the host module is `__main__`, so a by-name import executes a SECOND instance with its own lock and cache singletons - silent split-brain, not an ImportError. Host passes itself (or a narrow context object of the inventoried callables) at wiring time.
- **Facade re-exports:** the host keeps every extracted public symbol reachable under its original name so its own call sites stay verbatim and no unrelated diff appears.
- **Three load identities are three test cases:** host imported through the entry, host run directly as a script, and the authenticated static-help in-memory exec. Do not collapse them.
- Follow the tracker package's contract exactly - deterministic, stdlib-only, no per-command hashing inside the host source (`test_no_per_command_hashing` asserts the manifest literal never appears in flowctl.py).
- Do NOT change behavior. If the move surfaces a latent bug, record it and leave it - a fix inside a 'zero behavior change' extraction is unreviewable.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl_tracker/` - the pattern being copied: package layout, lazy load guard, soft-fail message shape, manifest
- `plugins/flow-next/scripts/flowctl.py` at the tracker package's lazy `sys.path.insert` guard sites - the load pattern to mirror
- `plugins/flow-next/tests/test_review_convergence_cap.py` and `test_review_convergence_journal.py` - the white-box invariants (locks, reservations, epochs, atomicity) that must pass unweakened against the new import path

**Optional** (reference as needed):
- `plugins/flow-next/scripts/flowctl_bootstrap.py` - the third load identity

### Key context
- This region is where review GATING lives; a subtle bug here decides whether work ships. Prefer stopping and reporting over improvising.
- The two convergence test files are the densest coverage in the repo - run them constantly during the move, not at the end.

### Acceptance
- [ ] Region lives in the new package; symbol list recorded in the task summary as the boundary (re-derived, not copied from stale coordinates); named stay-behind symbols still in the host
- [ ] Mechanical cross-boundary inventory recorded; every injected name traced to it
- [ ] Package contains no `import` of the host module by name; host injects context; missing injected symbol surfaces at wiring time naming the symbol
- [ ] Facade re-exports keep every extracted symbol reachable under its original name
- [ ] Behavior verified under all three load identities (entry-imported, direct script, authenticated static path)
- [ ] `test_prompt_text_pinned` green with unchanged hashes; no prompt constant moved
- [ ] Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_review_convergence_cap test_review_convergence_journal test_review_receipt_schema test_review_json_tallies test_flowctl_surface -q`

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
