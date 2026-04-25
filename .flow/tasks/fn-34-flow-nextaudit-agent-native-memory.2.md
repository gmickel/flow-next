---
satisfies: [R7, R8, R9, R10]
---

## Description

flowctl plumbing the skill (Task 1) calls. Add two tiny memory subcommands (`mark-stale`, `mark-fresh`), patch `cmd_memory_search` to honor `--status`, extend the memory schema for the two new optional fields. Pure persistence — no LLM dispatch, no subprocess chains, no engine.

**Size:** S → M (mostly small surface; M because it touches schema constants + 3 subcommands + tests)
**Files:**
- `plugins/flow-next/scripts/flowctl.py` (schema constants at 3657-3741; new `cmd_memory_mark_stale` + `cmd_memory_mark_fresh`; patched `cmd_memory_search` at 5851; argparse wiring at 15535-15719)
- `.flow/bin/flowctl.py` (lock-step copy after each change)
- `plugins/flow-next/tests/test_memory_mark_stale.py` (new)
- `plugins/flow-next/tests/test_memory_mark_fresh.py` (new)
- `plugins/flow-next/tests/test_memory_search_status.py` (new)
- `plugins/flow-next/tests/test_memory_schema.py` (extend — new fields validate)

## Approach

### Schema extension

Edit four constants near `flowctl.py:3657-3741`:

1. `MEMORY_OPTIONAL_FIELDS` — add `last_audited`, `audit_notes`. (Two fields. NOT `last_audited_hash` or `tree_sha` — those were artifacts of the old engine-based design.)
2. `MEMORY_FIELD_ORDER` — append the two new keys before `related_to`.
3. `_MEMORY_QUOTED_STRING_FIELDS` (line 3929) — add `last_audited`. Without quoting, PyYAML coerces ISO dates to `datetime.date`.
4. `validate_memory_frontmatter` (line 4567) — verify allowed-fields union picks up additions automatically. If it computes from constants, no edit. Otherwise add explicitly.

### `cmd_memory_mark_stale`

```python
def cmd_memory_mark_stale(args: argparse.Namespace) -> None:
    """Flag a memory entry as stale.

    Sets status: stale, last_audited (today), audit_notes (from --reason).
    Body preserved. Atomic via existing write_memory_entry.
    """
```

Flags:
- `<id>` (positional) — full id (`bug/runtime-errors/slug-2026-03-01`), slug+date, or slug-only (latest wins)
- `--reason "..."` — required; lands in `audit_notes`
- `--audited-by "..."` — optional; appended to `audit_notes` as `(audited-by: ...)`
- `--json` — machine-readable output

Implementation:
1. Resolve id via existing `_memory_resolve_id` helper (used by `cmd_memory_read`)
2. Read entry via `_memory_read_entry`
3. Mutate frontmatter dict: `status = "stale"`, `last_audited = today_iso()`, `audit_notes = reason + optional audited-by suffix`
4. Call `write_memory_entry(path, frontmatter, body)` — atomic + validated
5. Output success + path; or JSON `{success, id, path, status, last_audited, audit_notes}`

Idempotency: re-marking a stale entry updates `last_audited` and `audit_notes` (the new reason replaces the old). Body still untouched.

### `cmd_memory_mark_fresh`

```python
def cmd_memory_mark_fresh(args: argparse.Namespace) -> None:
    """Clear stale flag on a memory entry.

    Sets status to active (default), clears audit_notes, stamps last_audited.
    """
```

Flags:
- `<id>` (positional)
- `--audited-by "..."` — optional; appended to `audit_notes` (which becomes "marked fresh by X" or just blank)
- `--json`

Implementation:
1. Resolve id, read entry
2. Mutate: `status = "active"` (or omit — `active` is the default), clear `audit_notes` (or set to `"marked fresh"` for traceability — let's clear for cleanliness), `last_audited = today_iso()`
3. `write_memory_entry`
4. Output

If entry wasn't stale to begin with: still stamp `last_audited`. No-op on `status`. Idempotent.

### `cmd_memory_search` patch

Add `--status` argument to the search subparser, mirroring `cmd_memory_list:5673`:

```python
p_memory_search.add_argument(
    "--status", choices=["active", "stale", "all"], default="active"
)
```

In `cmd_memory_search` body (line ~5851), after the existing filter chain, add:

```python
if args.status != "all":
    results = [r for r in results if r.entry.frontmatter.get("status", "active") == args.status]
```

Mirror the exact pattern at `cmd_memory_list:5694-5699`. Apply BEFORE legacy results join (line ~5942) — legacy entries have no `status` so they default to `active`.

### Argparse wiring

In the memory subparser block near `flowctl.py:15700+`:

```python
p_memory_mark_stale = memory_sub.add_parser("mark-stale", help="Flag a memory entry as stale")
p_memory_mark_stale.add_argument("id")
p_memory_mark_stale.add_argument("--reason", required=True)
p_memory_mark_stale.add_argument("--audited-by")
p_memory_mark_stale.add_argument("--json", action="store_true")
p_memory_mark_stale.set_defaults(func=cmd_memory_mark_stale)

p_memory_mark_fresh = memory_sub.add_parser("mark-fresh", help="Clear stale flag")
p_memory_mark_fresh.add_argument("id")
p_memory_mark_fresh.add_argument("--audited-by")
p_memory_mark_fresh.add_argument("--json", action="store_true")
p_memory_mark_fresh.set_defaults(func=cmd_memory_mark_fresh)

# Existing p_memory_search — add the --status argument inline
p_memory_search.add_argument("--status", choices=["active", "stale", "all"], default="active")
```

### Lock-step `.flow/bin/flowctl.py` copy

After every edit to `plugins/flow-next/scripts/flowctl.py`:
```bash
cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py
```
Include in commit. Run smoke tests against both paths if possible.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:3657-3741` — schema constants (extension target)
- `plugins/flow-next/scripts/flowctl.py:3929` — `_MEMORY_QUOTED_STRING_FIELDS`
- `plugins/flow-next/scripts/flowctl.py:4567-4651` — `validate_memory_frontmatter` (verify pickup)
- `plugins/flow-next/scripts/flowctl.py:4009-4028` — `write_memory_entry` (atomic write helper to call)
- `plugins/flow-next/scripts/flowctl.py:4730-4750` — `_memory_read_entry` (read helper)
- `plugins/flow-next/scripts/flowctl.py:5526-5658` — `cmd_memory_read` (id resolution pattern; reuse `_memory_resolve_id` if exists, otherwise mirror)
- `plugins/flow-next/scripts/flowctl.py:5658-5778` — `cmd_memory_list` (`--status` filter pattern to mirror)
- `plugins/flow-next/scripts/flowctl.py:5851-...` — `cmd_memory_search` (patch site)
- `plugins/flow-next/scripts/flowctl.py:15535-15719` — argparse subparser registration

**Optional:**
- `plugins/flow-next/tests/test_memory_add.py` — test pattern reference (importlib + fixture style)
- `plugins/flow-next/tests/test_memory_list_read_search.py` — search-test pattern reference (if file exists)

## Key context

- `validate_memory_frontmatter` likely uses `MEMORY_REQUIRED_FIELDS | MEMORY_OPTIONAL_FIELDS | MEMORY_BUG_FIELDS | MEMORY_KNOWLEDGE_FIELDS` union for allowed-keys check. Verify by grep — if so, just adding to `MEMORY_OPTIONAL_FIELDS` is enough.
- `_MEMORY_QUOTED_STRING_FIELDS` controls YAML write quoting. `last_audited: 2026-04-25` without quotes → PyYAML reads back as `datetime.date(2026, 4, 25)` and round-trip writes break. Quote it.
- `audit_notes` doesn't need quoting unless it contains YAML-special chars (`:`, `#`, `[`, `{`). Existing `_format_memory_yaml_value` (or equivalent) likely handles auto-quoting. Verify.
- The `mark-stale` / `mark-fresh` helpers write `status` field which already exists in `MEMORY_OPTIONAL_FIELDS` and validates as `active|stale` per fn-30.
- Pure plumbing — no Ralph gate. The skill (Task 1) handles user-facing flow including Ralph behavior. flowctl helpers run unconditionally.

## Acceptance

- [ ] `MEMORY_OPTIONAL_FIELDS` includes `last_audited`, `audit_notes`. (R10)
- [ ] `MEMORY_FIELD_ORDER` includes the two new keys before `related_to`. (R10)
- [ ] `_MEMORY_QUOTED_STRING_FIELDS` includes `last_audited`. (R10)
- [ ] `validate_memory_frontmatter` accepts an entry with `last_audited` + `audit_notes` without raising. (R10)
- [ ] `flowctl memory mark-stale <id> --reason "X"` sets `status: stale`, `last_audited: <today>`, `audit_notes: "X"` on the entry. Body unchanged. (R7)
- [ ] `flowctl memory mark-stale <id> --reason "X" --audited-by "Y"` includes `(audited-by: Y)` suffix in `audit_notes`. (R7)
- [ ] `flowctl memory mark-stale <id> --json` returns documented JSON shape. (R7)
- [ ] `flowctl memory mark-stale` without `--reason` errors with usage message (argparse `required=True`). (R7)
- [ ] Re-marking an already-stale entry is idempotent (updates `last_audited` + `audit_notes`; no error). (R7)
- [ ] `flowctl memory mark-fresh <id>` clears `status` (back to active default), clears `audit_notes`, stamps `last_audited`. (R8)
- [ ] `flowctl memory mark-fresh` on a non-stale entry: stamps `last_audited`, no error (no-op on already-active). (R8)
- [ ] `flowctl memory search <q>` defaults to `--status active`, excludes stale-flagged entries. (R9)
- [ ] `flowctl memory search <q> --status stale` returns only stale entries. (R9)
- [ ] `flowctl memory search <q> --status all` returns both active + stale. (R9)
- [ ] `flowctl memory list --status stale` (existing) still works alongside the new search filter — no regression. (R9 partial)
- [ ] Unit tests in `tests/test_memory_mark_stale.py`, `tests/test_memory_mark_fresh.py`, `tests/test_memory_search_status.py`, extended `tests/test_memory_schema.py` cover the above. `python3 -m unittest discover -s plugins/flow-next/tests -v` — all green.
- [ ] `.flow/bin/flowctl.py` updated in lock-step after final edits. Both paths usable.


## Done summary

(populated when task completes)

## Evidence

(populated when task completes)
