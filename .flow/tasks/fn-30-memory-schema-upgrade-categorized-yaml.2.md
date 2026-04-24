# fn-30-memory-schema-upgrade.2 flowctl memory add with overlap detection + track/category args + backcompat --type

## Description

Rewrite `flowctl memory add` to use the new schema. Add overlap detection. Preserve backward compatibility for `--type pitfall|convention|decision` with deprecation warnings.

**Size:** M

**Files:**
- `plugins/flow-next/scripts/flowctl.py` — `cmd_memory_add`, overlap detector
- `.flow/bin/flowctl.py` (mirror)
- Unit tests (add to existing flowctl test suite if present; else `tests/flow-next/test_memory.py`)

## CLI signature

```
flowctl memory add \
  --track <bug|knowledge> \
  --category <category-from-enum> \
  --title <one-line> \
  [--module <module/file/subsystem>] \
  [--tags "tag1,tag2"] \
  [--body-file <path>] \
  [--problem-type <type>] \
  [--symptoms <one-line>] \
  [--root-cause <one-line>] \
  [--resolution-type <type>] \
  [--applies-when <one-line>] \
  [--no-overlap-check] \
  [--json]
```

- Body can also come from stdin: `echo "..." | flowctl memory add --body-file - ...`
- Date auto-set to today
- Slug derived from title

## Overlap detection

Before writing, scan the target `category/` directory for potential overlaps:

```python
def check_overlap(track: str, category: str, title: str, tags: list[str], module: str | None) -> dict:
    """
    Returns:
      {"level": "high", "matches": [entry_id, ...]} — existing entry to update
      {"level": "moderate", "matches": [entry_id, ...]} — create + related_to
      {"level": "low", "matches": []} — create standalone
    """
```

Matching dimensions (score 0-4):
1. Title substring overlap (fuzzy — normalize case + punctuation + split into tokens; ≥50% token overlap counts)
2. ≥1 tag match
3. Same module (if both entries specify it; skip dimension if either is unspecified)
4. Same category (implicit — always true for this scan)

Thresholds:
- Score ≥3: high → update existing (add `last_updated`, optionally merge new body into existing)
- Score 2: moderate → create new with `related_to: [existing-id]`
- Score ≤1: low → create new

On high:
- Print: `High overlap with <entry-id>. Updating existing entry instead of creating duplicate. (Override with --no-overlap-check.)`
- Update: set `last_updated`, append new body content under a "Update YYYY-MM-DD" heading (preserves history), merge tags (dedup)

On moderate:
- Print: `Moderate overlap with <entry-id>. Creating new entry with related_to reference.`
- Create entry with `related_to: [existing-id]` in frontmatter

On low or `--no-overlap-check`:
- Create standalone

## Backward compatibility

If `--type pitfall|convention|decision` is passed instead of `--track/--category`:

| Old | New (auto-mapped) |
|-----|---|
| `--type pitfall` | `--track bug --category build-errors` (or let fast-model classify if title+content clear; default to build-errors) |
| `--type convention` | `--track knowledge --category conventions` |
| `--type decision` | `--track knowledge --category tooling-decisions` |

Print deprecation warning:

> `--type` is deprecated; use `--track` and `--category`. Auto-mapped to `--track X --category Y`. (Suppress with `FLOW_NO_DEPRECATION=1`.)

Keep working for 2 minor releases, then remove. Document deprecation in CHANGELOG.

## JSON output

`--json` returns:

```json
{
  "success": true,
  "entry_id": "bug/runtime-errors/null-deref-in-auth-2026-05-01",
  "path": ".flow/memory/bug/runtime-errors/null-deref-in-auth-2026-05-01.md",
  "overlap_level": "low|moderate|high",
  "related_to": ["..."],
  "action": "created|updated",
  "warnings": []
}
```

## Acceptance

- **AC1:** `memory add --track bug --category runtime-errors --title "X"` creates `.flow/memory/bug/runtime-errors/x-YYYY-MM-DD.md` with valid frontmatter.
- **AC2:** `memory add --type pitfall` auto-maps to `--track bug --category build-errors` with deprecation warning (suppressible).
- **AC3:** Overlap detection identifies high overlap (title + tag + module match) and updates existing entry with `last_updated`.
- **AC4:** Overlap detection identifies moderate overlap and creates new entry with `related_to`.
- **AC5:** `--no-overlap-check` bypasses detection and always creates new entry.
- **AC6:** Missing required fields (`--title` etc.) return exit code 2 with helpful error.
- **AC7:** Invalid category (not in enum) returns exit code 2 with list of valid categories.
- **AC8:** Bug-track entries require `--problem-type`; knowledge-track entries require `--applies-when` (both via prompt if missing in interactive mode or fail in non-interactive).
- **AC9:** `--json` output matches schema above.
- **AC10:** Unit tests cover all overlap levels with synthetic seed entries.

## Dependencies

- fn-30-memory-schema-upgrade.1 (schema constants and templates)

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
