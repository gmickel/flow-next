---
satisfies: [R5, R7, R15, R16]
---

## Description

`flowctl prospect list / read / archive` subcommands + malformed artifact detection shared between Phase 0 (resume) and these commands.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/flowctl.py` (new: `cmd_prospect_list`, `cmd_prospect_read`, `cmd_prospect_archive`, `_prospect_parse_frontmatter`, `_prospect_detect_corruption`, argparse wiring)
- `.flow/bin/flowctl.py` (mirror)
- `plugins/flow-next/tests/test_prospect_cli.py` (new — unit tests)

## Approach

**`flowctl prospect list [--all] [--json]`:**
- Default: list `.flow/prospects/*.md` from last 30 days, active status only. Columns: `id`, `date`, `focus`, `survivor_count`, `promoted_count` (from `len(promoted_ideas)`), `status`.
- `--all`: include `_archive/` entries, stale (>30d), and corrupt. Add `path` column when showing `_archive/`.
- `--json`: emits `{success, artifacts: [...]}`.
- Sort: newest first; corrupt artifacts sort last with a note.

**`flowctl prospect read <artifact-id> [--section <name>] [--json]`:**
- Id resolution (parallels `cmd_memory_read`):
  - Full id: `dx-improvements-2026-04-24` → direct path lookup
  - Slug-only: `dx-improvements` → latest date wins
- `--section` optional: `focus | grounding | survivors | rejected` → print just that body section.
- `--json`: parse frontmatter + extract survivors/rejected as structured list.
- Corrupt artifact: print frontmatter + `[ARTIFACT CORRUPT: <reason>]` marker, exit 3 (distinct from 2 = Ralph-block).

**`flowctl prospect archive <artifact-id> [--json]`:**
- Move artifact to `.flow/prospects/_archive/`. Mkdir if missing.
- Update artifact frontmatter `status: archived` before move.
- Refuse if artifact is currently being extended (future-proofing; for now, just log a note).
- Never auto-archives — explicit user action only.

**Malformed artifact detection (R16):**
- Shared helper `_prospect_detect_corruption(path)` returns `None` for clean artifacts or a reason string:
  - `"frontmatter-parse-error"` — YAML doesn't parse
  - `"missing-required-section:<name>"` — `## Grounding snapshot` or `## Survivors` absent
  - `"missing-frontmatter-field:<name>"` — required field absent
  - `"empty"` — zero-byte file or whitespace only
  - `"unreadable"` — `OSError` on `open()` (matches the inline Phase 0 parser's behaviour)
- Used by both `list` (marks corrupt artifacts) and resume check (never offers corrupt for extension).
- Reuses existing YAML parser from memory subsystem (`_parse_inline_yaml` or similar — pick whichever is used by `validate_memory_frontmatter`).
- <!-- Updated by plan-sync: task 2 shipped an inline stdlib classifier in Phase 0 (skills/flow-next-prospect/workflow.md §0.2) emitting reason strings `"no frontmatter block" | "unparseable date" | "missing Grounding snapshot section" | "missing Survivors section" | "unreadable"`. This helper must either (a) replace the inline classifier — update workflow.md §0.2 to shell out to `flowctl prospect _detect-corruption` or import the helper — OR (b) match those exact reason strings byte-for-byte so R16's single-source-of-truth holds. Preferred path: land the helper here, then adapt Phase 0 in a follow-on touch-up commit (same task) to call it; reason-string contract must be identical across both call sites. -->

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:4917` (`cmd_memory_read`) — id-resolution pattern
- `plugins/flow-next/scripts/flowctl.py:5049` (`cmd_memory_list`) — listing + filter template
- `plugins/flow-next/scripts/flowctl.py:3958` (`validate_memory_frontmatter`) — parse + validate reuse
- `plugins/flow-next/scripts/flowctl.py` (argparse registry around `p_memory_*`) — subcommand registration pattern

**Optional:**
- `plugins/flow-next/scripts/flowctl.py` `cmd_memory_discoverability_patch` — path manipulation precedent

## Key context

- Id resolution must be robust: users will type partial slugs. Match `cmd_memory_read`'s precedence exactly (full id → slug+date → slug-only latest).
- `_archive/` prefix excludes artifacts from default `list` and `search` surfaces (convention matches `.flow/memory/_legacy/` and `.flow/memory/_audit/`).

## Acceptance

- [ ] `flowctl prospect list` with no args lists <30d active artifacts; `--all` includes stale/corrupt/archived.
- [ ] `flowctl prospect read <id>` accepts full id + slug-only; `--section` filters body; `--json` returns structured parse.
- [ ] `flowctl prospect archive <id>` moves to `_archive/` and updates frontmatter `status: archived`; mkdir if missing.
- [ ] `_prospect_detect_corruption` identifies: parse errors, missing required sections, missing required frontmatter fields, empty files.
- [ ] Corrupt artifacts surface via `list --all` with a reason note; `read` on corrupt artifact exits 3 with the reason.
- [ ] Unit tests cover: id resolution (3 cases), corruption detection (4 cases), archive move atomicity, list default vs `--all` filter, JSON output shape.
- [ ] All three commands support `--json` with consistent `{success, ...}` envelope.

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
