# Codex installer: honor CODEX_HOME for alternate homes

## Overview

A second Codex CLI home (`~/.codex-instances/work-cli`, a work account, a client sandbox) cannot receive flow-next's Codex surface. `install-codex.sh` hardcodes `CODEX_DIR="$HOME/.codex"`, and `sync-codex.sh` bakes the same literal into the generated mirror - so even a hand-copied second home reaches back into the primary `~/.codex` at runtime for flowctl and sibling scripts.

The fix is one substitution applied consistently: emit `${CODEX_HOME:-$HOME/.codex}` instead of `$HOME/.codex`, so a single artifact resolves correctly in every home at runtime. **The form already has in-repo precedent** - the mirror's `templates/spec.md` chain emits `${CLAUDE_PLUGIN_ROOT:-${DROID_PLUGIN_ROOT:-${CODEX_HOME:-$HOME/.codex}}}` today, so this generalizes an existing pattern rather than inventing one.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_precheck_mode_contract test_install_codex_legacy_cleanup test_codex_hooks_normalize -q
```

Idempotency (second run must produce no diff):

```bash
./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git diff --stat plugins/flow-next/codex/
```

Final gate, once:

```bash
python3 scripts/run_tests_parallel.py
uvx ruff@0.16.0 check .
```

## Goal & Context
<!-- scope: business -->

Multiple Codex CLI homes cannot receive flow-next's Codex surface. `scripts/install-codex.sh:37` hardcodes `CODEX_DIR="$HOME/.codex"` (plus literal `$HOME/.codex/hooks.json` uses at `:185`, `:188`), and `scripts/sync-codex.sh` bakes `$HOME/.codex` literals into the mirror artifacts. So even a hand-copied second home reaches back into the primary `~/.codex` at runtime for flowctl and sibling scripts.

The immediate driver is operational: installing flow-next into additional Codex instances without hand-editing generated files after every sync.

## Architecture & Data Models
<!-- scope: technical -->

**Two surfaces, one substitution.**

1. **`install-codex.sh`** - `CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"` at `:37`, and the two literal `$HOME/.codex/hooks.json` uses at `:185` / `:188` become `$CODEX_DIR/hooks.json`. Everything downstream already reads `$CODEX_DIR`.

2. **`sync-codex.sh`** - the rewrite sites currently emit the literal into generated artifacts. They must emit the runtime-evaluated form instead. Verified inventory of what the mirror carries today (57 occurrences across 46 files):

   | Emitted shape | Count |
   |---|---|
   | `$HOME/.codex/scripts/flowctl` | 50 |
   | `$HOME/.codex/skills/flow-next-resolve-pr/scripts` | 2 |
   | `$HOME/.codex/skills/flow-next-work/references/codex-delegation.md` | 1 |
   | `$HOME/.codex/plugin.json` | 1 |
   | `$HOME/.codex/agents` | 1 |
   | bare `$HOME/.codex` | 1 |
   | `${CLAUDE_PLUGIN_ROOT:-${DROID_PLUGIN_ROOT:-${CODEX_HOME:-$HOME/.codex}}}` (already correct) | 2 |

   **That inventory was incomplete and the "blanket rewrite is safe" claim built on it was wrong** (plan review, round 2). It grepped `$HOME/.codex` only. `sync-codex.sh:310-313` also emits the **tilde** form - `~/.codex/templates/flow-next-ralph-init` and `~/.codex/scripts` for ralph-init and worktree-kit - reaching 7 more mirror files. Those are executable paths bound to the primary home, so Ralph initialization and worktree-kit break under an alternate `CODEX_HOME`. Note also that `~` does not expand inside double quotes, so a quoted `cp "~/.codex/..."` is its own latent bug.

   The real inventory therefore covers **both spellings**, and each occurrence must be classified **executable vs narrative** rather than assumed uniform - some `$HOME/.codex` text is copied from canonical prose rather than produced by a rewrite site, and a parameter expansion displayed to a human as literal text is worse than the hardcoded path it replaced.

**The guards move with the form.** `sync-codex.sh` asserts the baked shape at `:1848`, `:1860-1864`, `:1984`. Those assertions are the thing that catches an unrewritten plugin-root reference escaping into the mirror - they must be retargeted to the new form, not deleted. A guard that stops matching is a guard that stops guarding.

**One test pins the literal**: `plugins/flow-next/tests/test_precheck_mode_contract.py`.

**The mirror diff will be large and is expected.** `plugins/flow-next/codex/` is generated; ~46 files change mechanically. Reviewers should read `sync-codex.sh` and spot-check the mirror, not read 46 generated diffs.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `CODEX_HOME=<tmpdir> ./scripts/install-codex.sh` installs entirely into `<tmpdir>` and writes nothing to `~/.codex`; with `CODEX_HOME` unset the script behaves exactly as today. Proven, not asserted: capture a recursive listing of `~/.codex` (paths plus mtimes) before and after the redirected install and require it byte-identical, so "nothing was written" is demonstrated rather than inferred from the absence of an error.
- **R2:** Installed skills and agents carry no executable reference bound to the primary home, in **either spelling** - `$HOME/.codex` or `~/.codex`. Every runtime path resolves through `${CODEX_HOME:-$HOME/.codex}`, including the ralph-init template and worktree-kit script paths emitted at `sync-codex.sh:310-313`. Occurrences are classified executable vs narrative; narrative mentions may remain literal under an explicit allowlist, and a new guard rejects any **executable** primary-home reference outside it. The existing guards at `:1848`, `:1860-1864`, `:1984` are retargeted to the new form and still fail on an unrewritten plugin-root reference - proven by a deliberate temporary break that the guard catches.
- **R3:** `README.md` documents the per-home install (`CODEX_HOME=<home> ./scripts/install-codex.sh`, run once per home).
- **R4:** `./scripts/sync-codex.sh` is byte-idempotent **across the second run**, proven by a check that works while the first run legitimately rewrites ~46 tracked files: hash the mirror after run 1, run it again, hash again, require the two hashes equal (`find plugins/flow-next/codex -type f -exec shasum {} + | shasum`). `git diff --stat` against HEAD cannot serve here - it reports the intended first-run regeneration and so can never be empty during this task, which made the original acceptance unsatisfiable. `test_precheck_mode_contract.py` and the existing Codex parity and no-drift tests stay green, updated where they pin the old literal, never relaxed to pass.
- **R5:** No new CLI flag, no Codex `config.toml` schema change, and no change to any other installer. `CODEX_HOME` is read from the environment only.
- **R6:** The installer's own test fixtures cannot escape into a real Codex home. `test_install_codex_legacy_cleanup.py`'s `_run_installer` redirects `HOME` but inherits `CODEX_HOME` from the ambient environment; once the installer honors that variable, a developer or CI runner with it exported would have the test install into - and run its cleanup logic against - their real home. Baseline tests must scrub inherited `CODEX_HOME`, an explicit temporary value must be supported, and a regression must prove the custom target receives the surface while the temporary primary home stays byte-identical.
- **R7:** Operator-facing output names the actual destination. The installer's error, progress, and completion messages hardcode `~/.codex` (`install-codex.sh:67`, `:437`, `:439`, `:441`, plus the hook-cleanup messages); an alternate-home install currently reports the wrong path, which defeats the operational check the feature exists for. Target-specific messages use `$CODEX_DIR`; generic documentation comments may keep the default.

## Boundaries
<!-- scope: business -->

- **Other installers are out of scope** - `install-cursor.sh`/`.ps1` and the marketplace paths are untouched.
- **No Codex `config.toml` schema work**, and no new flag: environment variable only.
- **No migration of an existing `~/.codex` install.** A primary home already installed keeps working unchanged; second homes are a fresh install each.
- **Not a multi-home management feature.** This makes one existing command reusable per home; it does not add listing, syncing, or switching between homes.

## Decision Context
<!-- scope: both -->

**Why `${CODEX_HOME:-$HOME/.codex}` rather than resolving at install time.** Baking the resolved absolute path per home would also work, but it makes every generated artifact home-specific, so the committed mirror could only ever be correct for one home. A runtime expansion keeps one mirror correct everywhere and keeps `sync-codex.sh` deterministic - the same input produces the same bytes regardless of who runs it or where.

**Why the guards must be retargeted rather than dropped.** They exist to catch a plugin-root reference that escaped the rewrite, which would expand to a broken `/skills/...` path inside Codex where neither variable is set. Changing the emitted form without moving the assertions leaves the mirror unguarded against exactly the class of regression this change could introduce.

**Why "nothing written to `~/.codex`" needs a before/after listing.** The failure mode is a path that silently falls back to the primary home. An install that errors is obvious; one that quietly writes to the wrong home is not, and that is the whole defect being fixed.

## Early proof point

Task .1 is the whole change. If the blanket substitution turns out to hit a site where the expansion is displayed rather than evaluated (narrative prose, a JSON string, a manifest field), stop and enumerate those sites before continuing - a `${VAR:-default}` shown to a human as literal text is a worse defect than the hardcoded path it replaced.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | `CODEX_HOME` redirects the install; unset behaves as today | .1 | - |
| R2 | No baked literal; guards retargeted and still biting | .1 | - |
| R3 | README per-home install line | .1 | - |
| R4 | sync idempotent; pinning tests updated not relaxed | .1 | - |
| R5 | No new flag, no schema change, no other installer touched | .1 | - |
| R6 | Installer tests cannot write to a real Codex home | .1 | - |
| R7 | Operator output names the actual destination | .1 | - |

## References

- `scripts/install-codex.sh:37` (`CODEX_DIR`), `:185`, `:188` (literal `hooks.json` paths)
- `scripts/sync-codex.sh` rewrite sites `:261`, `:271`, `:314`, `:315`, `:326`, `:1700`, `:1703`, `:1705`; guards `:1848`, `:1860-1864`, `:1984`
- Existing correct precedent in the mirror: the `templates/spec.md` chain already emits `${CODEX_HOME:-$HOME/.codex}`
- `plugins/flow-next/tests/test_precheck_mode_contract.py` (pins the literal)
- `README.md:129` (install section)
