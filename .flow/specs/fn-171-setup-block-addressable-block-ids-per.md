# setup-block: addressable block ids, multi-block state, read-only check verdict

## Goal & Context
<!-- scope: business -->

`flowctl setup-block` already does the careful parts of managing a region inside a mixed-ownership file: byte-preserving replacement between a marker pair, idempotent no-write `unchanged`, CRLF normalization before hashing, customization detection via pristine-hash transition, fail-closed on corrupt markers. But it is reachable for exactly one arrangement: a single span delimited by two compiled-in constants, with no read-only way to ask whether the span is still pristine.

Requested upstream as issue #294 (claims re-verified on 3.16.0: markers are module constants at flowctl.py:2543-2544, pristine state is one hash per path, the only verbs are the write paths `apply` and `resolve`). Three asks, one surface:

- (a) address a managed span by block id (marker pair derived from it);
- (b) key pristine state by `(path, block-id)` so several tracked regions can share a file;
- (c) a read-only `check` verb emitting the transition vocabulary, non-zero on drift, writing nothing - so CI (especially `setup_mode: copy` repos, where an edit is an ordinary reviewable diff) can assert a managed block was not hand-edited.

Value beyond third-party callers: flow-next itself carries three managed regions built three independent ways (setup-block in Python, the model-routing block as agent prose, `.flow/.gitignore`'s auto-managed block at flowctl.py:19129-19134). An id-keyed, multi-block primitive with a read-only verdict is the abstraction the tree is missing - though migrating those internal callers is explicitly out of scope here.

## Architecture & Data Models
<!-- scope: technical -->

All in the setup-block section of `plugins/flow-next/scripts/flowctl.py` (2543-2841; argparse at 47069-47088), plus dual-copy propagation, tracker-manifest regen, and codex mirror regen.

1. **Block id (a).** Optional `--id <BLOCK-ID>` on `apply`, `resolve`, and the new `check`. Default `FLOW-NEXT` derives exactly the current markers - zero behavior change for the two existing callers (setup skill workflow.md:828, 841-842). An explicit `--id FLOW-NEXT` is byte-identical to omitting the flag (normalized before keying - never a distinct state entry). Id validation (reject, never sanitize): non-empty, max 64 chars, charset `[A-Z0-9][A-Z0-9._-]*`, and NO `--` substring (HTML comments cannot contain `--`; a bad id would make its own marker line ambiguous). Custom id derives `<!-- BEGIN <ID> -->` / `<!-- END <ID> -->`.
2. **Per-id span resolution + scoped fail-close.** `_setup_block_span` (2563-2597) becomes id-parameterized: it scans ONLY for the given id's derived marker tokens. Corruption fail-close is scoped to the given id: an unpaired or embedded marker for id A fails an `--id A` operation; a stray marker belonging to a DIFFERENT id is opaque content, byte-preserved, validated only when that id is operated on. (Today's whole-file constant scan would brick id A on id B's stray marker - the mixed case is a required fixture.)
3. **Per-block state (b) - nested map, write-through upgrade.** `meta["setup"]["block_hashes"]` values become nested: `{<repo-relative-path>: {<id>: <hash-or-sentinel>}}`. NO flat composite string keys (a path can contain any separator character - nested is the only collision-free encoding). Tolerant read: a legacy string value is read as the default id's hash. Write path always writes the nested form; the first write to a path with a legacy string entry converts it (write-through upgrade - no standalone migration step, converges to one representation). The malformed-repair guards in `_setup_block_recorded_hash` / `_setup_block_record_hash` (2649-2688) MUST be rewritten for the dual shape: string value = legacy default-id entry (valid), dict-of-strings = nested (valid); only genuinely malformed values are repaired - never wipe valid entries of other shapes. The `resolve --choice keep` sentinel string `"customized"` lives per-(path,id) like any hash.
4. **Read-only `check` (c).** `flowctl setup-block check --file <target> --template <canonical> [--id <ID>] [--json]`. Computes the same classification `apply` computes - byte-equality FIRST, same as apply: a byte-pristine block is `unchanged`/exit 0 even when the recorded hash carries the `customized` sentinel. Zero writes: no target rewrite, no meta.json mutation, no hash re-record. It acquires the setup-block lock briefly for a consistent meta read (no mutation under it). Verdicts and exit codes:
   - exit 0: `unchanged` (byte-pristine).
   - exit 2 (drift): `template-drift` (block matches recorded pristine hash but not current template - apply would refresh), `customized` (differs, non-sentinel recorded hash or sentinel with real drift), `hash-absent` (differs, nothing recorded).
   - exit 3 (structural): `missing-file`, `missing-markers` (file exists, no pair for this id - what apply would treat as append territory), `corrupt` (unpaired/embedded marker for this id).
   - exit 1: ordinary errors (unreadable template, no .flow, bad id).
   The drift/structural verdict strings reuse apply's transition vocabulary where the states coincide (`unchanged`, `customized`, `hash-absent`) and name the read-only-only states (`missing-file`, `missing-markers`, `template-drift`, `corrupt`) - apply expresses those as actions or hard errors, so "no new synonyms" applies to shared states only. JSON reuses the `_setup_block_emit` shape (`target`/`action`/`reason`/`hash`, action = verdict); the standard result envelope's `command` field distinguishes check from apply emissions.
5. **CRLF.** `check` normalizes exactly as `apply` (`_setup_block_hash`, 2557-2560): CRLF-only difference is not drift. Mixed line endings across two managed spans in one file: byte-preservation outside the operated span holds; fixture required.
6. **No meta.json schema/drift suite exists** (gen_flow_config_schema.py covers .flow/config.json only) - decided no-op; do not create one in this spec.

## API Contracts
<!-- scope: technical -->

- `flowctl setup-block apply --file F --template T [--id ID] [--json]` - byte-for-byte today's behavior when `--id` omitted or `FLOW-NEXT`.
- `flowctl setup-block resolve --file F --template T --choice keep|overwrite [--id ID] [--json]` - sentinel recorded per (path, id).
- `flowctl setup-block check --file F --template T [--id ID] [--json]` - new; read-only; exit/verdict contract as above.
- `test_flowctl_surface.py:163-164` help-text pin gains the `setup-block check` line.
- Docs: `docs/flowctl.md` setup-block section (152-165) documents `--id`, multi-block state, and `check` incl. the CI recipe for copy-mode repos and the exit-code table. `agent_docs/setup-modes.md` (~line 26 invariants) notes per-(path,id) keying.

## Edge Cases & Constraints
<!-- scope: technical -->

- Two blocks, one file: apply id A, apply id B, hand-edit B -> `check --id A` exit 0, `check --id B` exit 2 `customized`. Core fixture (the reported bug's inverse: today the second apply overwrites the first's hash).
- Legacy bare-path meta entry honored for default id; first default-id write converts to nested; explicit `--id FLOW-NEXT` equals omitted flag in both read and write.
- Malformed-repair must not wipe valid nested entries (regression fixture: nested map survives a `_setup_block_record_hash` round-trip; parallel-apply merge fixture in test_portable_locks.py:152 extended to two ids on one path).
- Stray marker for id B present while operating id A: apply/check for A succeed; check/apply for B fail-close `corrupt`.
- `check` on byte-pristine block with `customized` sentinel recorded: `unchanged`, exit 0 (byte-equality first, matching apply's order).
- `check` writes nothing in ANY branch - fixture asserts meta.json and target mtimes/bytes unchanged, including the hash-absent and template-drift branches (apply re-records in those branches; check must not).
- Symlink-target rejection, mode preservation, atomic-write behavior unchanged (existing fixtures keep passing with default id).
- Setup skill call sites (workflow.md:828, 841-842) pass no `--id` - pinned as regression anchors.
- Windows CI runs these tests - no POSIX-only fixtures.

## Acceptance Criteria
<!-- scope: both -->

- R1: `apply`/`resolve`/`check` accept `--id`; omitted id and explicit `--id FLOW-NEXT` behave byte-for-byte as today (markers, hashes, transitions, existing test suite untouched-green). Errors: invalid id (charset, length, `--` substring, empty) rejected with a clear message before any file read.
- R2: A custom id operates on its own derived marker pair; content outside that pair - including other ids' managed spans and stray markers belonging to other ids - is byte-preserved and never triggers fail-close for the operated id. Errors: unpaired/embedded marker FOR THE OPERATED ID fails closed, no write.
- R3: Pristine state is a nested `{path: {id: hash}}` map: two managed blocks in one file are tracked independently; legacy bare-path string entries are read as the default id without a migration step and converted on first write; the malformed-repair guards accept both shapes and never wipe valid entries. Errors: genuinely malformed values (non-string, non-dict, dict with non-string leaves) repaired to `{}` for that entry only.
- R4: `setup-block check` is read-only in every branch (no target write, no meta.json mutation, no hash re-record), emits the verdict + exit-code contract from Architecture item 4 (byte-equality first; 0 pristine / 2 drift / 3 structural / 1 error), and supports `--json` in the `_setup_block_emit` shape. Errors: this IS the error surface - each structural verdict distinct.
- R5: The two-blocks-one-file fixture passes end-to-end: independent apply, independent drift detection, independent check verdicts, parallel-apply lock merge across two ids on one path.
- R6: CRLF-only differences are not drift in `check` (parity with apply's normalization); mixed-line-ending two-span fixture preserves bytes outside the operated span.
- R7: `docs/flowctl.md` + `agent_docs/setup-modes.md` document id, nested state, and the CI check recipe with exit codes; `test_flowctl_surface.py` pin updated; CHANGELOG under `## Unreleased` crediting @sn-furali (#294); dual copy + tracker manifest regen + sync-codex twice.

## Boundaries
<!-- scope: business -->

- NOT a policy engine; no opinion about what a consumer's block contains.
- NOT a payload-wide integrity verb over `.flow/bin/**` / templates (issue's optional extension) - separate spec if ever wanted.
- NOT migrating flow-next's other two managed regions (model-routing prose block at skills/flow-next-setup/references/, `.flow/.gitignore` block at flowctl.py:19129-19134) onto this primitive - tasks must not break them.
- NOT `--dry-run` on apply; `check` is the read-only path.
- NOT free-form `--begin/--end` marker overrides - ids only.
- NOT a meta.json schema/drift suite (none exists; decided no-op).

## Decision Context
<!-- scope: both -->

Issue #294's three asks shipped together (one surface); (c) alone was the reporter's minimal fallback but (a) unblocks third-party use. Markers derived from id, not free-form overrides: smaller surface, no escaping questions, id doubles as the state key. Gap-analysis resolutions: nested `{path: {id: hash}}` map (flat composite keys collide - paths can contain any separator); write-through upgrade of legacy entries (satisfies no-migration while converging on one representation); per-id-scoped fail-close (whole-file constant scan would brick id A on id B's stray marker); byte-equality-first in check (matches apply's order - a hand-reverted block is pristine, CI stays green); exit codes 0/2/3/1 so shell CI can gate without jq while JSON carries the exact verdict; check takes the lock briefly for a consistent read but never mutates. fn-160 overlap noted (setup-block state machine + adjacent meta keys): sequence or coordinate at work time; default-id path stays byte-identical so either order is safe.
