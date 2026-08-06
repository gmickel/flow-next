---
satisfies: [R1, R2, R3]
---
# fn-171-setup-block-addressable-block-ids-per.1 setup-block --id: derived markers, per-id span scoping, nested (path,id) state

## Description
---
satisfies: [R1, R2, R3]
---

### Description
Add `--id` to `apply`/`resolve` with id-derived marker pairs, per-id-scoped span resolution and fail-close, and the nested `{path: {id: hash}}` state map with tolerant legacy read + write-through upgrade.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_setup_block_helper.py`, `plugins/flow-next/tests/test_portable_locks.py`

### Approach
- Id validation (reject, never sanitize): non-empty, max 64, `[A-Z0-9][A-Z0-9._-]*`, no `--` substring; checked before any file read. Explicit `--id FLOW-NEXT` normalizes to the default - never a distinct state entry.
- Derive markers `<!-- BEGIN <ID> -->` / `<!-- END <ID> -->`; default id yields today's constants (2543-2544).
- `_setup_block_span` (2563-2597) id-parameterized: scan ONLY the given id's tokens; fail-close (unpaired/embedded) scoped to the operated id; a stray marker for a different id is opaque byte-preserved content.
- State: `meta["setup"]["block_hashes"]` becomes `{path: {id: hash-or-sentinel}}`. Tolerant read: legacy string value = default id's hash. Writes always nested; first write to a legacy-entry path converts it. Rewrite the malformed-repair guards in `_setup_block_recorded_hash`/`_setup_block_record_hash` (2649-2688) for the dual shape - string = valid legacy, dict-of-strings = valid nested; repair only genuinely malformed values, per entry, NEVER wiping the whole map.
- `resolve --id`: `customized` sentinel recorded per (path,id).
- Argparse (47069-47088): add `--id` to both subparsers.

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:2543-2841` - full setup-block section
- `plugins/flow-next/scripts/flowctl.py:47069-47088` - argparse registration
- `plugins/flow-next/tests/test_setup_block_helper.py:28-251` - fixture class + 12 existing tests (must stay green untouched)
- `plugins/flow-next/tests/test_portable_locks.py:152-167` - parallel-apply hash-map merge fixture

**Optional:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md:828,841-842` - the only callers (no --id; regression anchors)

### Key context
- Existing 12 tests green WITHOUT edits = the R1 byte-for-byte guarantee.
- Lock pattern: meta re-read inside `_setup_block_lock` (2717-2725) per call - replicate for nested writes; extend the parallel-merge fixture to two ids on one path (last-writer-wins per (path,id), never per path).
- Windows CI runs these tests - no POSIX-only fixtures.

### Acceptance
- [ ] Existing setup-block suite passes unmodified (R1)
- [ ] Invalid ids rejected before any file read (charset/length/`--`/empty) (R1)
- [ ] `--id FLOW-NEXT` == omitted, in read and write paths (R1)
- [ ] Custom id operates its own pair; other ids' spans + stray markers byte-preserved, no cross-id fail-close; operated-id corruption fails closed with no write (R2)
- [ ] Nested state map: two blocks in one file tracked independently; legacy string entries read as default id + converted on first write; repair guards accept both shapes, wipe nothing valid (R3)
- [ ] Parallel-apply merge across two ids on one path is lossless
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_setup_block_helper test_portable_locks -q`

## Acceptance
- [ ] --id on apply/resolve, derived markers, id validation
- [ ] per-id span scoping + scoped fail-close
- [ ] nested (path,id) state with tolerant legacy read + write-through upgrade
- [ ] existing suite green unmodified; two-id parallel merge lossless

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
