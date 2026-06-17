# fn-64-tracker-sync-project-flow-spec.1 flowctl: depRelations sync state + list/set/clear-dep-relation subcommands + unit tests

## Description
### Goal
Add the deterministic flowctl plumbing the dependency-projection hook stands on: a `depRelations` provenance list in per-spec tracker state, plus `flowctl sync` subcommands to enumerate dep edges and read/write projection provenance. **Satisfies R7, R9.**

### Investigation targets
- `plugins/flow-next/scripts/flowctl.py:1095` — `default_spec_tracker_state()`: add `depRelations: []` (provenance list of edge keys we created). Persisted in `.flow/specs/<id>.json` sidecar, NOT frontmatter.
- `flowctl.py:20090` `_resolve_sync_spec()` + `:20109` `_write_sync_state()` — reuse these + `atomic_write_json` / `_content_hash` / `now_iso`; never hand-roll writes/hashes.
- `flowctl.py:20236` `cmd_sync_set_merge_base` — model the provenance-write shape (hash provenance) but do NOT entangle with the paired-snapshot invariant; dep-relations are independent state.
- `flowctl.py:20320` `_iter_tracker_states()` — resolve a dep spec-id → its `tracker.id`/`identifier`/status (the blocked-by target).
- `flowctl.py:12909-12943` `cmd_spec_add_dep` — copy the idempotent append (expand_bare_spec_id + dedup no-op) pattern.
- `flowctl.py:23384-23523` — `sync` argparse subparser block; register `list-dep-relations`, `set-dep-relation`, `clear-dep-relation` following `p_sync_base` shape. Plug spec/tracker-id args into the existing ID canonicalizer (do not ad-hoc parse — memory: id-grammar-widening).
- Tests: `plugins/flow-next/tests/test_tracker_sync_state.py` — pure-stdlib `unittest`, in-process handler calls via `argparse.Namespace`, assert sidecar JSON read back from disk. Extend the `test_new_spec_sidecar_has_tracker_block` field loop for the new `depRelations` key.

### Notes
flowctl owns plumbing only (set field / list / atomic-write); the projection *decision* lives in the skill (fn-64.5). Verify field/enum/subcommand names against actual flowctl.py emitters before finalizing (memory: skill-prose-must-match-real-flowctl).
## Acceptance
- [ ] `flowctl sync list-dep-relations <spec-id> --json` → `[{dep_spec, dep_tracker_id, dep_identifier, dep_status, projected}]`; `dep_status` is the LOCAL dep-spec status (done/open) from flowctl, not a remote fetch.
- [ ] `depRelations[]` entry shape persisted: `{key:<opaque token>, dep_spec, from_tracker_id, to_tracker_id, type:"blocks", source:"flow", updatedAt}`; `key` is an opaque hash, never a raw issue key.
- [ ] `flowctl sync set-dep-relation` / `clear-dep-relation` write `depRelations` atomically (`_write_sync_state`); set is idempotent (dedup no-op, mirrors `cmd_spec_add_dep`).
- [ ] New `depRelations` defaults to `[]` on a fresh spec sidecar (`default_spec_tracker_state()`).
- [ ] Tracker-identifier validator widened to accept bare `N` (numeric) in addition to `#N` / `owner/repo#N`, so `sync set-tracker-id --identifier 42` succeeds; covered by a test.
- [ ] Self-edge guard: a spec depending on itself is skipped (no self relation) — enforced/representable in the listing.
- [ ] Unit tests (test_tracker_sync_state.py style) cover: add, idempotent rerun (no dup), missing-link warning, completed-blocker (local-`done`) surfaced, bare-`N` identifier acceptance, self-edge skip, sidecar field present.
- [ ] `python3 -m unittest discover -s plugins/flow-next/tests` green.
- [ ] CLI shape is concrete: `set-dep-relation <spec-id> --dep-spec <id> --from-tracker-id <id> --to-tracker-id <id> --type blocks --source flow`; `clear-dep-relation <spec-id> --dep-spec <id>` (or `--key`) removes the ledger entry. Documented in flowctl.md by fn-64.6.
## Done summary
flowctl dependency-relation plumbing (fn-64.1): added the `depRelations` provenance ledger to `default_spec_tracker_state()` (persisted in the spec sidecar), an opaque hashed edge-key helper (`_dep_relation_key`, never inlines a raw issue key per the auto-linkify pitfall), and three `flowctl sync` subcommands — `list-dep-relations` (enumerates `depends_on_epics` edges + resolves each dep's tracker link + local `dep_status` + `projected` flag), `set-dep-relation` (idempotent provenance write via `_write_sync_state`), and `clear-dep-relation`. Tracker-identifier validator widened to accept bare `N`. Self-edges skipped. `dep_status` is the LOCAL dep-spec status (the plan-review decision), not a remote fetch.
## Evidence
- Commits:
- Tests: python3 -m unittest discover -s plugins/flow-next/tests — 30+ green incl. test_set_dep_relation_records_entry_shape, test_bare_numeric_identifier_accepted, test_bare_zero_identifier_rejected
- PRs: