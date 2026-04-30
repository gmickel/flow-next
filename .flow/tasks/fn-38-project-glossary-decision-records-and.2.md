---
satisfies: [R1, R3, R4, R14, R15, R18]
---

## Description

Implement the glossary plumbing: `GLOSSARY.md` file format, nearest-ancestor resolution, and four flowctl subcommands. **This is the early proof point for the epic** — validates file format + walk algorithm + atomic writes round-trip cleanly. If this fails, downstream tasks (T3-T6) need revision before continuing.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/scripts/glossary_smoke_test.sh`

## Approach

- New helper `find_nearest_glossary(start: Path = Path.cwd()) -> Optional[Path]` near `flowctl.py:87`. **First-match-wins ancestor walk** (tsconfig pattern), bounded at `get_repo_root()` (gitignore convention), defensive 32-level cap (defends against pathological symlinks per practice-scout). Walk via `Path.parent`; do NOT manually follow symlinks (kernel handles `ELOOP`).
- New `parse_glossary_file(text: str) -> list[GlossaryEntry]`. Use stdlib `re.finditer` on `^##\s+(.+)$` (multiline). Pre-strip fenced code blocks via `re.sub(r'\`\`\`.*?\`\`\`', '', text, flags=re.DOTALL)`. Pre-normalize CRLF. Capture per term: heading text, definition paragraph (heading-end → next-heading-start), `_Avoid_:` italic line (regex `^_Avoid_:\s*(.+)$`), optional `_Relates to_:` anchor links.
- New `validate_glossary_entry(entry)` — schema check before write. Pattern from `validate_prospect_frontmatter` at `flowctl.py:4150-4182`. Required: term name + definition. Optional: avoid (list), relates_to (list).
- New `cmd_glossary_add/list/read/remove`. Pattern from `cmd_prospect_*` at `flowctl.py:7534-7952` (cleanest recent reference). **Atomic-rewrite**: read full file, mutate in-memory entry list, render, `atomic_write` whole file (`flowctl.py:798`). Whole-file replace is correct because glossary writes are coarse-grained.
- **Multi-line definitions:** `--definition "..."` stays single-line. `--definition-file -` reads stdin; `--definition-file <path>` reads file. Behavior (b) inline writes (T3) use stdin variant.
- **Write-target rule:** `add` writes to nearest-ancestor (matches read resolution). To force creation of a subdirectory glossary, drop an empty `GLOSSARY.md` first; subsequent `add` from inside that subtree writes to it. No `--scope` flag.
- Argparse `glossary` subparser registration after the `prospect_sub` block at `flowctl.py:15860-15928`.
- New smoke `plugins/flow-next/scripts/glossary_smoke_test.sh` (pattern from `audit_smoke_test.sh:1-90`): refuses to run from main repo; uses `/tmp/glossary-smoke-$$`. Cases: nearest-ancestor walk (root + subdir), atomic write, multi-line via stdin, parse roundtrip, `_Avoid_` aliases, term removal, last-term-removal hygiene (file becomes empty H1 husk → keep file or delete? — match Constraints: keep husk; husk re-trips autodetect-on but autodetect requires non-empty term list per T3 logic).
- **R18 verified by smoke:** `rm -rf .flow/` between two glossary-write phases; verify `GLOSSARY.md` files survive.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:87-99` — `get_repo_root` (anchor for ancestor walk)
- `plugins/flow-next/scripts/flowctl.py:798-809` — `atomic_write`
- `plugins/flow-next/scripts/flowctl.py:866-895` — `slugify` (term-name normalization for case-insensitive match)
- `plugins/flow-next/scripts/flowctl.py:4150-4182` — `validate_prospect_frontmatter` (schema-validation template)
- `plugins/flow-next/scripts/flowctl.py:7534-7952` — `cmd_prospect_*` (subcommand pattern)
- `plugins/flow-next/scripts/flowctl.py:15860-15928` — `prospect_sub` argparse registration template
- `plugins/flow-next/scripts/audit_smoke_test.sh:1-90` — smoke test structure

**Optional:**
- [open-gitops/documents/GLOSSARY.md](https://github.com/open-gitops/documents/blob/main/GLOSSARY.md) — real-world H2-per-term reference

## Acceptance

- [ ] `flowctl glossary add Term --definition "single-line def" --avoid "alias1,alias2"` writes to root `GLOSSARY.md` (creates if missing); single-line definition round-trips
- [ ] `flowctl glossary add Term --definition-file -` (stdin) accepts multi-line definition; round-trips with newlines preserved
- [ ] `flowctl glossary read Term` resolves via nearest-ancestor walk from cwd; subdir glossary wins when present, root wins otherwise (R3)
- [ ] `flowctl glossary list --json` returns terms grouped by file when multiple `GLOSSARY.md` files exist on the chain
- [ ] `flowctl glossary remove Term` deletes the entry from the file that defines it
- [ ] Nearest-ancestor walk stops at `get_repo_root()`, filesystem boundary (`st_dev` change), or 32-level cap; symlink loops do not hang (kernel `ELOOP` covered)
- [ ] `GLOSSARY.md` is human-readable markdown with H2-per-term sections (R15)
- [ ] No meta-file (e.g. `GLOSSARY-MAP.md`) is added in this task or anywhere in the codebase (R4 — verified by T7 grep guard)
- [ ] `rm -rf .flow/` does not affect any `GLOSSARY.md` file (R18 verified by smoke)
- [ ] `glossary_smoke_test.sh` passes (covers all the above + parse roundtrip + fenced-code stripping + last-term-removal hygiene)

## Done summary

## Evidence
