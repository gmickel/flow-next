---
satisfies: [R1, R2, R3]
---
# fn-156-codex-installer-honor-codex-home-for.1 Honor CODEX_HOME in install-codex.sh + sync-codex.sh rewrites

## Description
Size: S/M.

Files: `scripts/install-codex.sh`, `scripts/sync-codex.sh`, `plugins/flow-next/codex/*` (regenerated), affected tests in `plugins/flow-next/tests/`, `README.md`.

Investigation targets:
- `scripts/install-codex.sh:37` (`CODEX_DIR="$HOME/.codex"`), `:185`, `:188` (literal `$HOME/.codex/hooks.json`).
- `scripts/sync-codex.sh` skills rewrite sites `:261`, `:271`, `:314`, `:315`, `:326`; agents rewrites `:1700`, `:1703`, `:1705`; baked-form guards `:1848`, `:1860-1864`, `:1984`.
- `README.md:129` install section.

Do:
1. `CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"`; use `$CODEX_DIR/hooks.json` for the literal hooks.json paths.
2. sync-codex.sh: emit `${CODEX_HOME:-$HOME/.codex}` in place of the literal `$HOME/.codex` at the rewrite sites; move the guards/assertions to the new baked form; update tests asserting the old literal.
3. Re-run `./scripts/sync-codex.sh` twice so the mirror is regenerated and idempotent.
4. Add the one-line README note.

## Acceptance
- [ ] `CODEX_HOME=<tmpdir> ./scripts/install-codex.sh` writes only into `<tmpdir>`; nothing lands in `~/.codex`; unset `CODEX_HOME` behaves as today (R1).
- [ ] `grep -R '\$HOME/\.codex' plugins/flow-next/codex/` is clean of baked literals; artifacts resolve flowctl/scripts via `${CODEX_HOME:-$HOME/.codex}` at runtime; parity/sync tests green (R2).
- [ ] README documents `CODEX_HOME=<home> ./scripts/install-codex.sh`, once per home (R3).


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
