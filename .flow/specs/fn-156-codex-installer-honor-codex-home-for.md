# fn-156-codex-installer-honor-codex-home-for Codex installer: honor CODEX_HOME for alternate homes

## Overview
Multiple Codex CLI homes (e.g. `~/.codex-instances/work-cli` for a second account) cannot receive flow-next's Codex surface. `scripts/install-codex.sh:37` hardcodes `CODEX_DIR="$HOME/.codex"` (plus literal `$HOME/.codex/hooks.json` uses at :185, :188), and `scripts/sync-codex.sh` bakes `$HOME/.codex` literals into the mirror artifacts (skills rewrite sites :261, :271, :314, :315, :326; agents :1700, :1703, :1705; baked-form guards :1848, :1860-1864, :1984). So even a hand-copied second home reaches back into the primary `~/.codex` at runtime for flowctl and sibling scripts.

## Scope
In: `scripts/install-codex.sh`, `scripts/sync-codex.sh`, the regenerated `plugins/flow-next/codex/` mirror, affected tests under `plugins/flow-next/tests/`, one README line.
Out: other installers (`install-cursor.sh`, marketplace paths), Codex config.toml schema changes, any new CLI flag.

## Approach
1. `install-codex.sh`: `CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"`; replace the literal `$HOME/.codex/hooks.json` uses with `$CODEX_DIR/hooks.json` (cosmetic echo strings optional).
2. `sync-codex.sh`: emit `${CODEX_HOME:-$HOME/.codex}` instead of a literal `$HOME/.codex` at the rewrite sites — runtime-evaluated, so the same artifact works in every home. Move the baked-form guards/assertions to the new form and update any parity/no-drift tests that assert the literal.
3. Re-run `./scripts/sync-codex.sh` (twice, for idempotency) so `plugins/flow-next/codex/` reflects the new form.
4. README install section (~L129): one line — `CODEX_HOME=<home> ./scripts/install-codex.sh` installs/updates that home; run once per home.

## Quick commands
- `cd plugins/flow-next/tests && python3 -m unittest test_install_codex_legacy_cleanup test_codex_hooks_normalize -q`
- `./scripts/sync-codex.sh` (run twice; second run must be a no-op)

## Acceptance
- **R1:** `CODEX_HOME=<tmpdir> ./scripts/install-codex.sh` installs entirely into `<tmpdir>`; nothing is written to `~/.codex`; with `CODEX_HOME` unset the script behaves exactly as today.
- **R2:** Installed skills/agents contain no baked `$HOME/.codex` literal (grep clean); they resolve flowctl and sibling scripts via `${CODEX_HOME:-$HOME/.codex}` at runtime; existing parity/sync tests stay green.
- **R3:** README documents the per-home install command.

## References
- `scripts/install-codex.sh:37`, `:185`, `:188`
- `scripts/sync-codex.sh:261`, `:271`, `:314`, `:315`, `:326`, `:1700`, `:1703`, `:1705`, `:1848`, `:1860-1864`, `:1984`
- `README.md:129`
