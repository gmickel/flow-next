---
satisfies: [R6, R7, R8, R9]
---

## Description

flowctl plumbing for fn-35. Three concrete changes:

1. **Add** `flowctl memory list-legacy [--json]` — wraps `_memory_parse_legacy_entries` per file in `MEMORY_LEGACY_FILES`; emits parsed segments with mechanical defaults the skill consumes.
2. **Drop** the codex/copilot subprocess dispatch chain — six functions (~225 LoC) at `flowctl.py:6403-6627`. Keep `_memory_classify_mechanical` (mechanical fallback) and `_memory_parse_legacy_entries` (parser).
3. **Collapse** `cmd_memory_migrate` to mechanical-only with deprecation hint. Preserve JSON receipt shape (`method` + `model` keys present) for backcompat. Keep `--no-llm` flag accepted-but-noop.

Pure plumbing — no LLM dispatch, no subprocess invocation. The skill (Task 1) does intelligence.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/flowctl.py` (changes around 6403-6627 removal, 6720-6970 collapse, ~15904 argparse insert)
- `.flow/bin/flowctl.py` (lock-step copy)
- `plugins/flow-next/tests/test_memory_list_legacy.py` (new — list-legacy subcommand)
- `plugins/flow-next/tests/test_memory_migrate.py` (extend if exists, otherwise new — verifies mechanical-only path + deprecation hint)

## Approach

### Add `cmd_memory_list_legacy`

```python
def cmd_memory_list_legacy(args: argparse.Namespace) -> None:
    """List legacy flat-file memory entries with parsed segments + mechanical defaults.

    Used by /flow-next:memory-migrate skill to enumerate entries before
    classifying them into the categorized schema.
    """
```

Logic:
1. Resolve memory dir (existing helper)
2. Iterate `MEMORY_LEGACY_FILES` (`pitfalls.md`, `conventions.md`, `decisions.md`)
3. For each file present: call `_memory_parse_legacy_entries(path)` → list of `{title, body, tags, date}` dicts
4. Augment each entry with `mechanical_track` + `mechanical_category` from `_memory_classify_mechanical(filename)` (returns `(track, category)` tuple)
5. Output:
   - Text mode: human-readable list (`pitfalls.md (2 entries):` etc.)
   - JSON mode: `{files: [{filename, entry_count, entries: [{title, body, tags, date, mechanical_track, mechanical_category}]}]}`

Argparse insertion alongside `p_memory_migrate` near `flowctl.py:15904`:

```python
p_memory_list_legacy = memory_sub.add_parser("list-legacy", help="List legacy flat-file memory entries with mechanical default classifications")
p_memory_list_legacy.add_argument("--json", action="store_true")
p_memory_list_legacy.set_defaults(func=cmd_memory_list_legacy)
```

### Drop subprocess dispatch chain

Remove the following from `flowctl.py` (line ranges from repo-scout):
- `_memory_classify_build_prompt` — 6403-6437
- `_memory_classify_parse_response` — 6440-6465
- `_memory_classify_run_codex` — 6468-6508
- `_memory_classify_run_copilot` — 6511-6561
- `_memory_classify_select_backend` — 6564-6587
- `_memory_classify_entry` — 6590-6627

**Preserve:**
- `_memory_classify_mechanical` (6390-6400) — mechanical fallback, used by `cmd_memory_migrate` and `cmd_memory_list_legacy`
- `_memory_parse_legacy_entries` (6359-6387) — parser, used by both consumers above

**Verify post-removal:**
- Grep for `FLOW_MEMORY_CLASSIFIER_BACKEND`, `FLOW_MEMORY_CLASSIFIER_MODEL`, `FLOW_MEMORY_CLASSIFIER_EFFORT` — should be zero hits in flowctl.py after removal
- Grep for orphaned imports (`subprocess`, `shutil.which` if newly unused)
- Half-removed `if backend == "codex"` chains: remove the entire if/elif block, not just the codex/copilot legs

### Collapse `cmd_memory_migrate`

Function lives at `flowctl.py:6720-6970+`. Current structure:

```
1. Parse args
2. Detect legacy files
3. Pick classifier backend (LLM-dispatch logic to remove)
4. Build per-entry plan: parse + classify + compute target path
5. Confirm with user (interactive y/N)
6. Write categorized entries
7. Output report
```

After collapse:
```
1. Parse args
2. Emit deprecation hint to stderr (if TTY, once per process)
3. Emit env-var warning if FLOW_MEMORY_CLASSIFIER_* set (once per process)
4. Detect legacy files
5. Build per-entry plan: parse + mechanical-classify + compute target path
   (no backend selection; always mechanical)
6. Confirm with user (interactive y/N) — unchanged
7. Write categorized entries — unchanged
8. Output report (with method="mechanical", model=null in JSON shape)
```

Specific edits in `cmd_memory_migrate`:
- Remove `backend, model, effort = _memory_classify_select_backend()` (~6756-6760)
- Remove `backend_failed_once = False` (~6769) and the fallback warning logic (~6778-6795)
- Replace `_memory_classify_entry(...)` call (~6778) with direct call to `_memory_classify_mechanical(filename)` returning `(track, category)`
- In plan dict (~6807-6809): set `method = "mechanical"` always; `model = None` always
- JSON output keys preserved: `method` (always `"mechanical"`), `model` (always `null`)

### Deprecation hint pattern

Add to `cmd_memory_migrate` (and reuse for `cmd_memory_list_legacy` if appropriate — but probably only on migrate since list-legacy is the new path):

```python
def _emit_migrate_deprecation_hint() -> None:
    """One-time stderr deprecation hint for migrate's mechanical-only path."""
    # Module-level guard to print once per process
    global _MIGRATE_DEPRECATION_PRINTED
    if _MIGRATE_DEPRECATION_PRINTED:
        return
    if not sys.stderr.isatty():
        return  # don't pollute --json pipelines
    print(
        "[DEPRECATED] Subprocess-based classification removed. "
        "Now mechanical-only by default.\n"
        "For agent-native classification, use: /flow-next:memory-migrate",
        file=sys.stderr,
    )
    _MIGRATE_DEPRECATION_PRINTED = True
```

Plus a one-time env-var deprecation warning:

```python
def _check_dead_classifier_env_vars() -> None:
    """One-time stderr warning for dead FLOW_MEMORY_CLASSIFIER_* env vars."""
    dead_vars = [
        v for v in ("FLOW_MEMORY_CLASSIFIER_BACKEND", "FLOW_MEMORY_CLASSIFIER_MODEL", "FLOW_MEMORY_CLASSIFIER_EFFORT")
        if os.environ.get(v)
    ]
    if not dead_vars:
        return
    if not sys.stderr.isatty():
        return
    print(f"[DEPRECATED] {', '.join(dead_vars)} no longer used; classification now runs in-skill (/flow-next:memory-migrate).", file=sys.stderr)
```

Both helpers called early in `cmd_memory_migrate`. Module-level `_MIGRATE_DEPRECATION_PRINTED = False` guard.

### Lock-step `.flow/bin/flowctl.py`

After all edits to `plugins/flow-next/scripts/flowctl.py`:
```bash
cp plugins/flow-next/scripts/flowctl.py .flow/bin/flowctl.py
```
Include in commit.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:6390-6400` — `_memory_classify_mechanical` (preserve)
- `plugins/flow-next/scripts/flowctl.py:6359-6387` — `_memory_parse_legacy_entries` (preserve, wrap)
- `plugins/flow-next/scripts/flowctl.py:6403-6627` — six functions to remove
- `plugins/flow-next/scripts/flowctl.py:6720-6970` — `cmd_memory_migrate` (collapse target)
- `plugins/flow-next/scripts/flowctl.py:5481, 6737` — `MEMORY_LEGACY_FILES` constant references
- `plugins/flow-next/scripts/flowctl.py:~15904` — argparse subparser insertion point (after `p_memory_migrate`)

**Optional:**
- `plugins/flow-next/tests/test_memory_add.py` — test pattern (importlib + fixture)
- `plugins/flow-next/scripts/smoke_test.sh:1927-1997` — existing migrate smoke (uses `--no-llm` exclusively; nothing to update post-collapse)

## Key context

- `--no-llm` flag becomes a no-op after collapse but is **kept accepted** so scripted callers don't break. argparse entry stays at line ~15919-15924.
- JSON receipt shape MUST preserve `method` + `model` keys for backcompat (additive schema rule from CLAUDE.md). Set to `"mechanical"` / `null` post-collapse.
- Deprecation hint suppressed in non-TTY (pipes / scripts) — protects `--json` consumers from polluted stderr.
- Module-level `_MIGRATE_DEPRECATION_PRINTED` guard ensures hint prints once per Python process — running migrate over 50 entries doesn't spam.
- Env-var deprecation warning is separate from the migrate-was-LLM hint. Users with vars set need explicit notice; users without don't.
- After removal, audit the file for unused imports (`subprocess` if it was only used by the classifier dispatch — likely still used elsewhere; verify).

## Acceptance

- [ ] `flowctl memory list-legacy` (text mode) lists entries from existing legacy files with mechanical default labels. (R6)
- [ ] `flowctl memory list-legacy --json` returns `{files: [{filename, entry_count, entries: [{title, body, tags, date, mechanical_track, mechanical_category}]}]}`. (R6)
- [ ] `flowctl memory list-legacy` on a repo with no legacy files outputs "No legacy files found" (text) or `{files: []}` (json), exits 0. (R6)
- [ ] Six classifier functions removed: `_memory_classify_run_codex`, `_memory_classify_run_copilot`, `_memory_classify_select_backend`, `_memory_classify_build_prompt`, `_memory_classify_parse_response`, `_memory_classify_entry`. (R7)
- [ ] `_memory_classify_mechanical` and `_memory_parse_legacy_entries` preserved. (R7)
- [ ] grep for `FLOW_MEMORY_CLASSIFIER_BACKEND` / `_MODEL` / `_EFFORT` returns zero hits in flowctl.py. (R7)
- [ ] No orphaned `subprocess.run` calls left over from removed functions. (R7)
- [ ] `flowctl memory migrate --yes` (no `--no-llm`) runs mechanical-mode classification, succeeds, JSON output has `method: "mechanical"`, `model: null`. (R8)
- [ ] `flowctl memory migrate --no-llm --yes` runs identically (the flag is now a no-op but accepted). (R8)
- [ ] `flowctl memory migrate` (TTY, no flags, no input) emits stderr deprecation hint mentioning `/flow-next:memory-migrate`. (R9)
- [ ] `flowctl memory migrate --yes --json | jq .` runs cleanly with no stderr pollution to stdout. (R9)
- [ ] When `FLOW_MEMORY_CLASSIFIER_BACKEND=codex` is set in env, running `flowctl memory migrate` (TTY) emits stderr warning naming the dead env vars. (R9)
- [ ] Both deprecation hints fire only once per process, not per entry. (R9)
- [ ] Existing `smoke_test.sh:1927-1997` migrate block still passes after the collapse (it uses `--no-llm` which is now a no-op).
- [ ] New unit tests in `tests/test_memory_list_legacy.py` and `tests/test_memory_migrate.py` (extend) cover the above. `python3 -m unittest discover -s plugins/flow-next/tests -v` — all green.
- [ ] `.flow/bin/flowctl.py` updated in lock-step.


## Done summary

(populated when task completes)

## Evidence

(populated when task completes)
