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
- Shared helper `_prospect_detect_corruption(path)` returns `None` for clean artifacts or a reason string. <!-- Updated by plan-sync: task 3 landed the Phase 0 inline classifier in skills/flow-next-prospect/workflow.md §0.2 with the reason strings below. This helper must match them byte-for-byte so R16 has a single source of truth, OR replace the Phase 0 inline parser by importing `_prospect_detect_corruption` (preferred: land helper here + adapt §0.2 in a follow-on touch-up commit within this same task). -->
  - `"no frontmatter block"` — YAML frontmatter block missing (file has no `---` delimiter pair at top)
  - `"unparseable date"` — `date` field absent or not `YYYY-MM-DD` parseable
  - `"missing Grounding snapshot section"` — `## Grounding snapshot` heading absent
  - `"missing Survivors section"` — `## Survivors` heading absent
  - `"unreadable"` — `OSError` on `open()` (matches the inline Phase 0 parser's behaviour)
- Also emit `"empty"` for zero-byte / whitespace-only files (no existing Phase 0 coverage — this helper extends the contract; Phase 0 touch-up must add the same branch).
- Used by both `list` (marks corrupt artifacts) and resume check (never offers corrupt for extension).
- Reuses `validate_prospect_frontmatter` from task 3's shipped flowctl.py helpers to check `PROSPECT_REQUIRED_FIELDS` presence (emit `"missing frontmatter field: <name>"` for missing keys; keep reason string format consistent with the others). <!-- Updated by plan-sync: task 3 shipped `PROSPECT_REQUIRED_FIELDS` + `validate_prospect_frontmatter` (flowctl.py §3958-4081) — reuse directly instead of rolling a parallel checker. -->

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:4917` (`cmd_memory_read`) — id-resolution pattern
- `plugins/flow-next/scripts/flowctl.py:5049` (`cmd_memory_list`) — listing + filter template
- `plugins/flow-next/scripts/flowctl.py:3958` — shipped prospect helpers from task 3: `PROSPECT_REQUIRED_FIELDS`, `PROSPECT_STATUS_VALUES`, `validate_prospect_frontmatter`, `write_prospect_artifact`, `render_prospect_body`, `_prospect_slug`, `_prospect_next_id`. Reuse for parse + validate; build a companion parser (invert the writer's YAML output) for `cmd_prospect_read`. <!-- Updated by plan-sync: task 3 shipped these bundled helpers; task 4 reuses rather than duplicating. -->
- `plugins/flow-next/scripts/flowctl.py` (argparse registry around `p_memory_*`) — subcommand registration pattern
- `plugins/flow-next/skills/flow-next-prospect/workflow.md:48-132` — Phase 0 inline corruption classifier; reason strings are the R16 contract.

**Optional:**
- `plugins/flow-next/scripts/flowctl.py` `cmd_memory_discoverability_patch` — path manipulation precedent

## Key context

- Id resolution must be robust: users will type partial slugs. Match `cmd_memory_read`'s precedence exactly (full id → slug+date → slug-only latest).
- `_archive/` prefix excludes artifacts from default `list` and `search` surfaces (convention matches `.flow/memory/_legacy/` and `.flow/memory/_audit/`).

## Acceptance

- [ ] `flowctl prospect list` with no args lists <30d active artifacts; `--all` includes stale/corrupt/archived.
- [ ] `flowctl prospect read <id>` accepts full id + slug-only; `--section` filters body; `--json` returns structured parse.
- [ ] `flowctl prospect archive <id>` moves to `_archive/` and updates frontmatter `status: archived`; mkdir if missing.
- [ ] `_prospect_detect_corruption` identifies: parse errors, missing required sections, missing required frontmatter fields, empty files. Reason strings match the Phase 0 inline classifier contract (workflow.md §0.2): `"no frontmatter block" | "unparseable date" | "missing Grounding snapshot section" | "missing Survivors section" | "unreadable"`, plus helper-added `"empty"` and `"missing frontmatter field: <name>"` variants. <!-- Updated by plan-sync: reason strings aligned with shipped Phase 0 classifier for R16 single-source-of-truth. -->
- [ ] Corrupt artifacts surface via `list --all` with a reason note; `read` on corrupt artifact exits 3 with the reason.
- [ ] Unit tests cover: id resolution (3 cases), corruption detection (4 cases), archive move atomicity, list default vs `--all` filter, JSON output shape.
- [ ] All three commands support `--json` with consistent `{success, ...}` envelope.

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
