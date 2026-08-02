---
satisfies: [R1, R2, R3, R4, R5, R6, R7]
---
# fn-156-codex-installer-honor-codex-home-for.1 Honor CODEX_HOME in install-codex.sh + sync-codex.sh rewrites

## Description
Make one existing command reusable per Codex home by replacing a hardcoded path with a runtime-evaluated one, in both the installer and the generator that bakes it into the mirror.

**`scripts/install-codex.sh`** - `CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"` at `:37`; the two literal `$HOME/.codex/hooks.json` uses at `:185` and `:188` become `$CODEX_DIR/hooks.json`. Everything downstream already reads `$CODEX_DIR`, so those three edits are the whole installer change.

**`scripts/sync-codex.sh`** - the rewrite sites must emit `${CODEX_HOME:-$HOME/.codex}` instead of the literal, so one generated artifact resolves correctly in every home. Sites: `:261`, `:271`, `:314`, `:315`, `:326` (skills) and `:1700`, `:1703`, `:1705` (agents).

**Verified inventory of what the mirror carries today** - 57 occurrences across 46 files, all executable path references inside bash blocks rather than narrative prose, which is what makes a blanket substitution safe:

| Emitted shape | Count |
|---|---|
| `$HOME/.codex/scripts/flowctl` | 50 |
| `$HOME/.codex/skills/flow-next-resolve-pr/scripts` | 2 |
| `$HOME/.codex/skills/flow-next-work/references/codex-delegation.md` | 1 |
| `$HOME/.codex/plugin.json` | 1 |
| `$HOME/.codex/agents` | 1 |
| bare `$HOME/.codex` | 1 |

**The inventory above is INCOMPLETE - plan review caught it.** It greps `$HOME/.codex` only. `sync-codex.sh:310-313` also emits the **tilde** form (`~/.codex/templates/flow-next-ralph-init`, `~/.codex/scripts`) for ralph-init and worktree-kit, reaching 7 more mirror files. Those are executable paths bound to the primary home, so Ralph init and worktree-kit break under an alternate `CODEX_HOME`. Build the real inventory over **both spellings**, and classify each occurrence **executable vs narrative** - a `${VAR:-default}` displayed as literal text is worse than the hardcoded path. Note `~` does not expand inside double quotes, so a quoted `cp "~/.codex/..."` is a latent bug of its own.

**The form already has in-repo precedent.** The mirror's `templates/spec.md` chain emits `${CLAUDE_PLUGIN_ROOT:-${DROID_PLUGIN_ROOT:-${CODEX_HOME:-$HOME/.codex}}}` today. Follow that shape rather than inventing a new one.

**Retarget the guards, do not delete them.** `sync-codex.sh` asserts the baked shape at `:1848`, `:1860-1864`, `:1984`. They exist to catch a plugin-root reference that escaped the rewrite - which would expand to a broken `/skills/...` path inside Codex where neither variable is set. Move the assertions to the new form. A guard that stops matching is a guard that stops guarding, and this change is exactly the kind that could introduce what it guards against.

**The installer's own tests can escape into a real Codex home - fix that in the same change.** `plugins/flow-next/tests/test_install_codex_legacy_cleanup.py:70` builds its env as `dict(os.environ, HOME=str(home))`: it redirects `HOME` but inherits `CODEX_HOME`. Harmless today because the installer ignores it; once it honors it, anyone with `CODEX_HOME` exported runs the installer - and its cleanup logic - against their real home. Scrub inherited `CODEX_HOME` for baseline tests, support an explicit temporary value, and add a regression proving the custom target receives the surface while the temporary primary home stays byte-identical.

**Operator output must name the real destination.** `install-codex.sh:67`, `:437`, `:439`, `:441` and the hook-cleanup messages hardcode `~/.codex`, so an alternate-home install reports the wrong path - which defeats the operational check this feature exists for. Use `$CODEX_DIR` in target-specific messages; generic doc comments may keep the default.

Then regenerate the mirror, update the one test that pins the literal, and add the README line.

**Size:** M
**Files:** `scripts/install-codex.sh`, `scripts/sync-codex.sh`, `plugins/flow-next/codex/**` (generated, ~46 files), `plugins/flow-next/tests/test_precheck_mode_contract.py`, `README.md`

### Approach

- The mirror is generated: never hand-edit `plugins/flow-next/codex/`. Change `sync-codex.sh`, then re-run it twice and commit the result.
- Match the existing precedent form exactly; do not introduce a second spelling of the same idea.
- `test_precheck_mode_contract.py` pins the old literal. Update it to the new form - do not relax the assertion to something that would pass either way.

### Investigation targets

**Required** (read before coding):
- `scripts/install-codex.sh:30-45`, `:180-195` - `CODEX_DIR` and the two hooks.json literals
- `scripts/sync-codex.sh:250-330` - the skills rewrite sites
- `scripts/sync-codex.sh:1690-1710` - the agents rewrite sites
- `scripts/sync-codex.sh:1840-1870`, `:1980-1990` - the guards that assert the baked shape
- `plugins/flow-next/tests/test_precheck_mode_contract.py` - the test pinning the literal

**Optional** (reference as needed):
- Any mirror file carrying `${CODEX_HOME:-$HOME/.codex}` already, for the precedent shape

### Key context

Do NOT hand-edit anything under `plugins/flow-next/codex/` - it is generated by `sync-codex.sh` and a hand edit is erased by the next run.

Do NOT add a CLI flag or touch Codex `config.toml`. `CODEX_HOME` is read from the environment only.

Do NOT touch `install-cursor.sh` / `.ps1` or the marketplace paths.

The mirror diff will be large (~46 files) and mechanical. That is expected; the reviewable change is `sync-codex.sh` plus `install-codex.sh`.

If any rewrite site turns out to be narrative prose or a JSON/manifest string rather than an executable path, STOP and enumerate those sites before continuing - a `${VAR:-default}` displayed to a human as literal text is worse than the hardcoded path it replaced.
## Acceptance
- [ ] `install-codex.sh` uses `CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"` and `$CODEX_DIR/hooks.json` at both former literal sites (R1)
- [ ] `sync-codex.sh` emits `${CODEX_HOME:-$HOME/.codex}` at every skills and agents rewrite site (R2)
- [ ] BOTH spellings are clean: no executable `$HOME/.codex` and no executable `~/.codex` survives in `plugins/flow-next/codex/` outside a `${CODEX_HOME:-...}` default; `sync-codex.sh:310-313` (ralph-init templates, worktree-kit scripts) is rewritten (R2)
- [ ] Occurrences are classified executable vs narrative, and a new guard rejects executable primary-home references outside an explicit narrative allowlist (R2)
- [ ] `test_install_codex_legacy_cleanup.py` scrubs inherited `CODEX_HOME` for baseline tests, supports an explicit temporary value, and gains a regression proving the custom target gets the surface while the temporary primary home stays byte-identical (R6)
- [ ] Installer error/progress/completion messages use `$CODEX_DIR` so an alternate-home install reports the real destination (`:67`, `:437`, `:439`, `:441`, hook-cleanup) (R7)
- [ ] The `:1848` / `:1860-1864` / `:1984` guards are retargeted to the new form and still FAIL on an unrewritten plugin-root reference - demonstrate with a deliberate temporary break, then revert it (R2)
- [ ] Real-install proof: capture a recursive listing of `~/.codex` with mtimes, run `CODEX_HOME=<tmpdir> ./scripts/install-codex.sh`, and assert the listing is byte-identical afterwards while `<tmpdir>` received the full surface (R1)
- [ ] With `CODEX_HOME` unset the installer targets `~/.codex` exactly as before (R1)
- [ ] `test_precheck_mode_contract.py` updated to the new form, not relaxed (R4)
- [ ] `./scripts/sync-codex.sh` is byte-idempotent across the SECOND run, proven by hashing the mirror after run 1 and after run 2 and requiring equality (`find plugins/flow-next/codex -type f -exec shasum {} + | shasum`). `git diff --stat` cannot serve - the first run legitimately rewrites ~46 tracked files, so it can never be empty during this task (R4)
- [ ] `README.md` documents `CODEX_HOME=<home> ./scripts/install-codex.sh`, run once per home (R3)
- [ ] No new flag, no `config.toml` change, no other installer touched (R5)
- [ ] `## Unreleased` CHANGELOG entry; no version bump
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` and `uvx ruff@0.16.0 check .`
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
