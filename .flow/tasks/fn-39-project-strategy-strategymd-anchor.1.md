# fn-39-project-strategy-strategymd-anchor.1 flowctl strategy plumbing (status/read/list + helpers)

## Description
Implement `flowctl strategy` Python plumbing in `plugins/flow-next/scripts/flowctl.py`: constants, parse/render helpers, single-root walk, three subcommands (`status`, `read`, `list`), argparse registration. Mirror the glossary plumbing shape exactly — same constants pattern, same parse/render rhythm, same atomic-write contract.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/flowctl.py` (additive — new constants, helpers, `cmd_strategy_*` handlers, argparse subparser)

This is the foundation task. Tasks 2-6 all consume the JSON shapes that ship here. Frontmatter sentinel parse round-trip + husk detection + atomic write + single-root walk all freeze in this task.

## Approach

- Add module constants near `GLOSSARY_FILE` (`flowctl.py:63`):
  - `STRATEGY_FILE = "STRATEGY.md"`
  - `STRATEGY_GENERATOR = "flow-next-strategy"`
  - `STRATEGY_REQUIRED_SECTIONS = ("Target problem", "Our approach", "Who it's for", "Key metrics", "Tracks")`
  - `STRATEGY_OPTIONAL_SECTIONS = ("Milestones", "Not working on")`
  - `STRATEGY_HUSK_SENTINEL` (constant for the placeholder body string used to detect "section exists but empty")
- Add helpers near glossary helpers (`flowctl.py:148-405`):
  - `find_strategy_file(start_path)` — single-root walk: walks UP from `start_path` to first `STRATEGY.md`, capped at repo root via `get_repo_root()`. Different from `find_nearest_glossary` — strategy is repo-wide, NOT nearest-ancestor. Returns `(path, None)` if found, `(None, repo_root)` if absent.
  - `parse_strategy_file(text)` — returns `{name, last_updated, generator, target_problem, approach, personas, metrics, tracks, milestones, not_working_on}`. Reuse `_glossary_strip_fenced_code` for fence masking (`flowctl.py:266`). Use H2 heading regex similar to glossary's. Frontmatter parsed via existing YAML helper.
  - `render_strategy_file(parsed)` — emits H1 `# <name> Strategy` + frontmatter + H2 sections in locked order. Optional sections omitted if empty. Always emits H1 + frontmatter even when all sections empty (husk).
  - `validate_strategy_frontmatter(fm)` — requires `name`, `last_updated`, `generator: flow-next-strategy`. Refuses unknown keys (single-source-of-truth invariant).
  - `_strategy_section_filled(body)` — returns True if section body has at least one non-whitespace, non-comment prose line. False if body is empty, only HTML comments, or only the husk sentinel `_Not currently tracking._`.
- Add subcommand handlers near `cmd_glossary_*` (`flowctl.py:8563-8812`):
  - `cmd_strategy_status(args)` — calls `find_strategy_file(cwd)`. Returns `{exists: bool, husk: bool, sections_filled: int, total_sections: int, last_updated: str|null, file_path: str|null}`. Husk = file exists AND `sections_filled == 0`. `total_sections` counts populated optional + all required = 5..7.
  - `cmd_strategy_read(args)` — calls `find_strategy_file(cwd)`. If `--section <name>` provided, filter to one block (case-insensitive section name match via existing helpers). Returns full parse otherwise. Refuses `--section` for sections not in the locked list.
  - `cmd_strategy_list(args)` — single-root, returns `{groups: [{path, sections, count}], file_count, total_sections}`. For v1: `groups` has 0 or 1 element. Kept for parallel symmetry with `cmd_glossary_list`.
  - All three accept `--json` and emit via existing `json_output` helper.
- Argparse registration near glossary at `flowctl.py:16547-16622`:
  - Parent `strategy` parser → required `strategy_cmd` subparser → 3 children (`status`, `read`, `list`)
  - All children accept `--json`
  - `read` accepts `--section <name>`
- Foreign-file detection: `cmd_strategy_status` returns `{generator: <value-from-frontmatter or null>, generator_match: bool}`. Skill (Task 2) uses this to gate the migrate/keep/rewrite question.
- Atomic write contract: NO write subcommand in flowctl. Skill writes the file via host agent's `Write` tool. flowctl is read-only for strategy. (Mirrors `/flow-next:audit` pattern — flowctl marks stale, skill does the editing.)

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:63-64` — `GLOSSARY_FILE` / `GLOSSARY_WALK_MAX_DEPTH` constants pattern
- `plugins/flow-next/scripts/flowctl.py:148-208` — `find_nearest_glossary` walk algorithm (CONTRAST — strategy uses single-root walk, not nearest-ancestor)
- `plugins/flow-next/scripts/flowctl.py:260-405` — glossary parse/render/validate helpers (model for strategy equivalents)
- `plugins/flow-next/scripts/flowctl.py:8563-8812` — `cmd_glossary_*` subcommand handlers (direct model for `cmd_strategy_*`)
- `plugins/flow-next/scripts/flowctl.py:16547-16622` — glossary argparse registration (direct model)

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:266-279` — `_glossary_strip_fenced_code` (reuse for strategy parse fence masking)
- `plugins/flow-next/scripts/flowctl.py:401-405` — `_glossary_term_matches` (case-insensitive compare contract — reuse if section name fuzzy match needed)
- `plugins/flow-next/skills/flow-next-strategy/references/strategy-template.md` — section structure reference (Rumelt-derived: 5 required + 2 optional, no Marketing)

## Key context

- Strategy file is single-root, NOT nearest-ancestor like glossary. Strategy is repo-wide by Rumelt's definition; no monorepo subproject cascade.
- Frontmatter has exactly 3 keys: `name`, `last_updated`, `generator: flow-next-strategy`. Refuse unknown keys to keep audit story simple.
- No `add` / `edit` / `remove` subcommands. Skill writes the file. This task is read-only plumbing.
- Husk semantics align with glossary precedent: `sections_filled == 0` means file exists but no signal. Downstream autodetect uses count-based check, not file-existence.
- `cmd_strategy_*` use shared `atomic_write` helper at `flowctl.py:8669,8796` — even though the skill does the writing, downstream may want to write via flowctl in v2; reserve the helper for that.
## Acceptance
- [ ] Module constants `STRATEGY_FILE`, `STRATEGY_GENERATOR`, `STRATEGY_REQUIRED_SECTIONS`, `STRATEGY_OPTIONAL_SECTIONS` defined near `GLOSSARY_FILE` (`flowctl.py:63`); `STRATEGY_REQUIRED_SECTIONS` matches the locked Rumelt-derived template (5 sections); `STRATEGY_OPTIONAL_SECTIONS` is `("Milestones", "Not working on")` — no Marketing.
- [ ] `find_strategy_file(start)` walks UP from `start` to first `STRATEGY.md`, capped at `get_repo_root()`. Single-root semantics — does NOT do nearest-ancestor walk. Returns `(path, None)` if found, `(None, repo_root)` if absent at repo root.
- [ ] `parse_strategy_file(text)` returns dict with keys `{path, name, last_updated, generator, target_problem, approach, personas, metrics, tracks, milestones, not_working_on}`. Fenced code blocks masked during parse via `_glossary_strip_fenced_code`. CRLF normalized.
- [ ] `render_strategy_file(parsed)` round-trips: `parse → render → parse` produces byte-identical output for all populated sections; whitespace within section bodies preserved.
- [ ] `validate_strategy_frontmatter(fm)` requires `name`, `last_updated`, `generator: "flow-next-strategy"`. Refuses unknown frontmatter keys (returns error / non-zero RC); refuses different generator value.
- [ ] `_strategy_section_filled(body)` returns False for empty body, body containing only HTML comments, or body containing only the husk sentinel `_Not currently tracking._`. Returns True for any prose paragraph.
- [ ] `flowctl strategy status [--json]` returns JSON `{exists, husk, sections_filled, total_sections, last_updated, file_path, generator, generator_match}`. Husk = `exists AND sections_filled == 0`. `generator_match` is true only when frontmatter generator value equals `flow-next-strategy`.
- [ ] `flowctl strategy read [--section <name>] [--json]` returns full parsed dict. With `--section`, returns only the named section body. Section name matched case-insensitively against required+optional list; refuses unknown section names. Walks single-root via `find_strategy_file`.
- [ ] `flowctl strategy list [--json]` returns `{groups: [{path, sections, count}], file_count, total_sections}` with degenerate single-element group for v1. `count` is the per-file populated section count.
- [ ] Argparse registration: parent `strategy` parser registered next to glossary parser; required `strategy_cmd` subparser routes to status/read/list; all children accept `--json`.
- [ ] All three subcommands work from a repo subdirectory — walk reaches repo-root `STRATEGY.md` correctly.
- [ ] Husk file (`# Strategy\n` + frontmatter + zero sections) correctly classified: `flowctl strategy status --json | jq '.husk == true and .sections_filled == 0'` returns true.
- [ ] Last-section-deletion-leaves-husk invariant: removing all populated sections via `Write` of a frontmatter-only file → `flowctl strategy status` reports `husk: true`; subsequent `read` succeeds and returns empty bodies.
- [ ] `flowctl strategy read --section invalid-name --json` exits non-zero with structured error.
- [ ] `flowctl strategy status --json` outside any repo (no `git rev-parse` parent) returns `{exists: false, file_path: null}` cleanly without traceback.
- [ ] Round-trip preserves `last_updated` ISO date format YYYY-MM-DD; rejects non-ISO via `validate_strategy_frontmatter`.
- [ ] No `flowctl strategy add` / `edit` / `remove` / `section-set` subcommands exist — only status / read / list.
## Done summary
Implemented `flowctl strategy` read-only Python plumbing in `plugins/flow-next/scripts/flowctl.py`: STRATEGY_FILE/GENERATOR/sections/sentinel constants, `find_strategy_file` (single-root walk resolved relative to `start` not process cwd), `parse_strategy_file` / `render_strategy_file` / `validate_strategy_frontmatter` / `_strategy_section_filled` helpers, and three subcommands (`status`, `read [--section]`, `list`) registered alongside glossary in argparse. Verified end-to-end with 64 inline Python smoke checks covering round-trip, husk detection, validation rejection cases, single-root walk from subdirs, foreign-file detection, and outside-a-repo behavior; existing 210 smoke tests (flowctl + glossary) still pass.
## Evidence
- Commits: 42c6e3b1f845dd64a7a73645946cae601782f0fe
- Tests: python3 inline-smoke (64 checks: parse round-trip, husk detection, validate rejections, _strategy_section_filled edges, single-root walk, outside-repo, foreign-file, CLI subprocess subdir, last-section husk, PyYAML date), plugins/flow-next/scripts/smoke_test.sh (130/130 pass), plugins/flow-next/scripts/glossary_smoke_test.sh (80/80 pass)
- PRs: