# Troubleshooting

Common recovery patterns for stuck tasks, broken state, Ralph debugging, and review-backend conflicts. For deeper subsystem guides see [`flowctl.md`](flowctl.md) (CLI reference), [`ralph.md`](ralph.md) (Ralph internals), and the parent [`../README.md`](../README.md).

## Just updated the plugin and something is off? Re-run `/flow-next:setup`

The **single most common post-update issue.** `flowctl` (in `.flow/bin/`) and `.flow/usage.md` are **snapshot copies inside your repo**, written by setup - a plugin update (`/plugin` update, `droid plugin update`, or `git pull` + re-install on Codex/Cursor) refreshes the *plugin* but NOT those in-repo copies. So symptoms like a `flowctl` flag that "should exist" erroring, an outdated `.flow/usage.md`, or the skills printing `Local setup vX differs from plugin vY. Run /flow-next:setup to refresh local scripts` on stderr all mean the same thing:

```bash
/flow-next:setup      # re-copies launchers + flowctl.py + tracked fast-path files, rewrites usage.md,
                      # refreshes the model-routing scaffold + spec template, re-stamps setup_version
```

It is idempotent and non-destructive (your specs/tasks/memory/config are untouched). **Copy-mode repos only:** re-run it in **each project** after every flow-next update - not just once globally, because the copies live per-repo under `.flow/`. **Plugin-mode repos** (Claude Code, `setup_mode: "plugin"` in `.flow/meta.json`) have no local copies to refresh - plugin updates land silently and this section does not apply. See [platforms.md → Setup modes](platforms.md#setup-modes-plugin-vs-copy-fn-121).

## Pre-1.0 `.flow/epics/` layout still present?

`flowctl migrate-rename` / `migrate-rollback` are gone. Port by hand: rename `.flow/epics/` -> `.flow/specs/`, rewrite `next_epic`/`epic`/`epic_id` keys per `.flow/usage.md` "Pre-1.0 layout porting", then `flowctl validate --all`.

## Reset a stuck task

```bash
# Check task status
flowctl show fn-1.2 --json

# Reset to todo (from done/blocked)
flowctl task reset fn-1.2

# Reset + dependents in same spec
flowctl task reset fn-1.2 --cascade
```

`--cascade` walks the spec's `depends_on` graph and resets every downstream task that referenced the target, so the next `flowctl ready` call surfaces them again.

## Clean up `.flow/` safely

Run manually in terminal (not via AI agent — destructive command guards block agents from running `rm -rf`):

```bash
# Remove all flow state (keeps git history)
rm -rf .flow/

# Re-initialize
flowctl init
```

Or run `/flow-next:uninstall` to clean up docs and get the commands printed for manual execution.

## Debug Ralph runs

```bash
# Check run progress
cat scripts/ralph/runs/*/progress.txt

# View iteration logs
ls scripts/ralph/runs/*/iter-*.log

# Check for blocked tasks
ls scripts/ralph/runs/*/block-*.md
```

Each Ralph run lives under `scripts/ralph/runs/<timestamp>/`. The directory contains the iteration log, receipts (review / walkthrough / blocked), and an optional `progress.txt` tail. Deep dive: [`ralph.md`](ralph.md).

## Receipt validation failing

```bash
# Check receipt exists
ls scripts/ralph/runs/*/receipts/

# Verify receipt format
cat scripts/ralph/runs/*/receipts/impl-fn-1.1.json
# Must have: {"type":"impl_review","id":"fn-1.1",...}
```

Ralph reads receipts to decide whether to advance, retry, or block. A missing or malformed receipt freezes the loop. The bundled `flowctl validate --all` checks state-file shape; receipt-shape errors usually mean a backend wrote the file mid-iteration and the loop crashed.

## Review loop runs away (many rounds, never converges — fixed in fn-90)

**Symptoms:** a plan/impl/completion review loops far more than the ~3-round cap — the field report was **~11×** on a large ticket before the reviewer and implementer converged. Most common on the **Cursor** review backend, but the underlying causes were backend-agnostic.

**What was happening (root causes, all fixed in fn-90):**
- **The cap was prose-only and reset every invocation.** `MAX_REVIEW_ITERATIONS` (default 4) was an instruction to the host LLM to keep an in-context counter — but it reset to 0 on every *fresh* review invocation (a new Ralph iteration, a new pilot tick, a human retry). The runaway was ≈ 5–6 fresh invocations × ~3 in-agent rounds. Now flowctl owns a **cumulative counter on spec state** that survives fresh invocations and **refuses at the cap** (exit `4` + `ESCALATE:`).
- **Every re-review was a fresh blind review** (a churn lottery — two identical fresh Cursor reviews overlapped on only ~50% of findings, so SHIP was statistically near-unreachable within the cap). Now a **convergence ratchet** injects the prior round's findings with a shrink-only contract (verify each prior finding fixed; only a NEW ≥ Major finding may block; all prior fixed + no new ≥ Major ⇒ MUST SHIP).
- **Codex/copilot verdicts could be poisoned** by a verdict literal echoed in tool output (e.g. a grep of `smoke_test.sh`'s assertions), making flowctl report SHIP while the reviewer said NEEDS_WORK — a false SHIP *or* a false NEEDS_WORK that kept a loop alive. The parse now isolates the final agent message (last-match).
- **Cursor's ambient injection** (its built-in persona rubric + auto-attached `AGENTS.md`) diluted the scope anchor. A **persona-override preamble** now rides in every cursor review prompt (see [`orchestration.md`](orchestration.md)).

**What to do if you hit the cap now:**
- The review command exits with code **`4`** and an `ESCALATE:` message — this is **NOT retryable**. Under Ralph/autonomous it surfaces as NEEDS_HUMAN. A human should look at whether the plan/diff genuinely needs re-work (the reviewer strictness is often *signal* — big/ambiguous plans really do re-fail).
- After an explicit **re-plan** (you rewrote the spec/approach, not just patched a finding), reset the counter to re-open the cap: `flowctl spec reset-review-rounds <spec-id>` (add `--impl` to also clear per-task impl-review counters). A `SHIP` verdict resets it automatically.
- Raise the cap for a genuinely large ticket via `MAX_REVIEW_ITERATIONS` (env / Ralph `config.env`) — but prefer escalation: the cap is a backstop, the ratchet is the actual convergence fix.
- Full semantics: [`flowctl.md` § Deterministic review cap](flowctl.md#codex-impl-review) and [`ralph.md` § Review Loops Until SHIP](ralph.md#3-review-loops-until-ship).

## Review reports a model downgrade / floor (fn-76 resolution ladder)

**Symptom:** a review prints one stderr line like

```
warning: codex model 'gpt-5.6-sol' unavailable; downgraded to 'gpt-5.5'. Cached temporarily for this CLI version and routing intent.
```

(or `… fell back to the never-fail floor (the CLI default / 'auto')`), and the review's receipt records `gpt-5.5` / `auto` / `default` rather than the ranking top.

**This is expected, not an error.** flow-next dispatches the *strongest* model by default and, when the local CLI can't run it, transparently resolves the best available one (the [model-resolution ladder](flowctl.md#model-resolution-strongest-available-never-fail--fn-76)). It fires ONLY on the distinctive model-unavailable signature (codex *"requires a newer version of Codex"*, copilot *`… from --model flag is not available`*, cursor *`Cannot use this model: …`*); auth / network / sandbox / timeout failures propagate unchanged.

**What to do:**
- **Want the top model?** Upgrade the backend CLI (e.g. `codex` ≥ 0.144 for `gpt-5.6-sol`). The cache key is `(backend, CLI version, effective routing intent)`, so a CLI or routing change re-resolves automatically on the next review.
- **The downgrade repeats every review?** It normally should not — the result is memoized in `.flow/.cache/model-resolution.json`. A changed routing role, CLI version, or the 24-hour stronger-model re-probe intentionally causes one fresh resolution. Otherwise, the cache file may be unwritable; check permissions.
- **Force a specific model** (skip the ladder + cache entirely): pin it explicitly — `--spec codex:gpt-5.5`, a per-task/per-spec `review:` value, `FLOW_CODEX_MODEL`, or `review.backend`. An explicit unavailable model errors clearly instead of downgrading.
- **Reset the cache:** `rm -rf .flow/.cache/` — it is regenerated (and gitignored) on the next review; a corrupt file is already treated as a cold start.

## Custom rp-cli instructions conflicting

> **Caution**: If you have custom instructions for `rp-cli` in your `CLAUDE.md` or `AGENTS.md`, they may conflict with Flow-Next's RepoPrompt integration.

Flow-Next's plan-review and impl-review skills include specific instructions for `rp-cli` usage (window selection, builder workflow, chat commands). Custom rp-cli instructions can override these and cause unexpected behavior.

**Symptoms:**
- Reviews not using the correct RepoPrompt window
- Builder not selecting expected files
- Chat commands failing or behaving differently

**Fix:** Remove or comment out custom rp-cli instructions from your `CLAUDE.md`/`AGENTS.md` when using Flow-Next reviews. The plugin provides complete rp-cli guidance.

> **Note:** RepoPrompt is macOS-only. On non-Mac hosts without `rp-cli` on PATH, `/flow-next:plan` and `/flow-next:plan-review` don't propose the RepoPrompt path at all — `plan`'s setup offers Codex / export / none for review (research defaults to `repo-scout`), and `plan-review` steers only to the cross-platform backends (`codex`, `copilot`, `cursor`, `none`). `/flow-next:impl-review` and `/flow-next:spec-completion-review` apply the same gate to their steering (glance lists, ASK-error and override hints). An explicit `--review=rp` is still accepted and errors at runtime if `rp-cli` is missing.

## Copilot review backend on Windows (fixed in 1.1.9)

Spec-driven `flowctl copilot {impl,plan,completion}-review` calls work on native Windows from 1.1.9 onwards. No action required — the WSL detour from the 1.1.8 era is no longer necessary.

**What changed:** the POSIX path passes the prompt via `copilot -p "<text>"` (argv) which collides with Windows' `CreateProcessW` 32,767-char limit for spec-sized prompts. From 1.1.9, `run_copilot_exec` detects `sys.platform == "win32"` and switches to stdin delivery (`subprocess.run(input=prompt, ...)`) — bypassing the argv cap entirely. Stdin-mode `--resume` is resume-only (unlike `-p` mode's create-or-resume), so flow-next uses `--session-id=<uuid>` on the first call and `--resume=<uuid>` afterwards, tracked via a touch marker under `.flow/tmp/copilot-sessions/<uuid>`.

POSIX (macOS / Linux / WSL) behavior is unchanged.

**If you still see Windows argv errors:** check `flowctl --version` — anything below 1.1.9 hits the cap. Update with `flowctl setup` or pull the latest plugin.

**Upstream:** [github/copilot-cli#3398](https://github.com/github/copilot-cli/issues/3398) tracks a first-class `--prompt-file` flag. Once that lands, both POSIX and Windows paths will move to the cleaner file-based delivery.

## Windows: `python3` not found / Microsoft Store alias stub (fixed in fn-77)

**Symptom:** on Windows, `flowctl` fails with *"Python was not found; run without arguments to install from the Microsoft Store…"* and exit code **9009**, even though you installed real Python.

**Cause:** `python3` resolves to the Microsoft Store **App Execution Alias** — a 0-byte reparse point at `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe` that Windows ships **enabled by default**. When your real Python came from [python.org](https://python.org) or the `py` launcher (not the Store), the stub shadows it: it satisfies `command -v python3` (it *is* on `PATH`) but is non-functional. Older flowctl launchers trusted presence over function and picked the stub — so flow-next broke on every Windows machine in this configuration.

**The shipped fix (no action needed on a fresh install):** the `flowctl` launchers now probe interpreter functionality **and require Python 3.11+** in order `$PYTHON_BIN` → `py -3` → `python3` → `python`, so the 9009 stub and working-but-too-old interpreters are skipped before `flowctl.py` loads. If no candidate works, the error says so; if candidates work but are below 3.11, a distinct error tells you to install or select a supported Python. A `flowctl.cmd` batch shim ships alongside the extensionless bash `flowctl`, so PowerShell / cmd.exe (Claude Desktop, native Codex, native Cursor) resolve a supported interpreter too. See [`platforms.md` → Windows: Python discovery](platforms.md#windows-python-discovery).

**Recovering an already-broken install** (a pre-fix `.flow/bin/flowctl` hardcodes `exec python3` and cannot fix itself). Pick either:

1. **Re-stamp the launchers (recommended, durable).** `flowctl init` re-writes `.flow/bin/flowctl` **and** `.flow/bin/flowctl.cmd` from the fixed source. Because the broken bash launcher can't run, drive `init` through a working interpreter directly — `init` lives inside `flowctl.py`, so it never needs the launcher:

   ```powershell
   py -3.11 .flow/bin/flowctl.py init   # or use an explicit Python 3.11+ command
   ```

   or just re-run `/flow-next:setup` (its upgrade branch re-stamps both). After this, `flowctl` and `flowctl.cmd` work in every shell.

2. **Disable the Store alias (per-machine OS workaround).** Settings → Apps → Advanced app settings → **App execution aliases** → toggle **OFF** for `python.exe` **and** `python3.exe`. `python3` then resolves to your real install. Note the `py` launcher is [not included with Store Python](https://learn.microsoft.com/windows/python/faqs), so if you were relying on Store Python, install python.org Python (which ships `py`) to get `py -3`.

Prefer path 1 — the alias toggle is per-machine, not durable, and does not survive a fresh Windows profile.

**Sources:** Microsoft Learn [Python on Windows FAQ](https://learn.microsoft.com/windows/python/faqs) (the App Execution Alias stub + "the py launcher is not included with Store Python" + disabling the alias); python.org [Using Python on Windows](https://docs.python.org/3/using/windows.html) and [PEP 397](https://peps.python.org/pep-0397/) (the `py` launcher / `py -3`).

## `/flow-next:map` — clawpatch not found / version mismatch / Node 20

`/flow-next:map` wraps the upstream `clawpatch` CLI. Three common failure modes:

**1. `clawpatch` binary missing.** Skill prints `pnpm add -g clawpatch` install instructions verbatim and exits 1. No auto-install — global npm/pnpm installs are user-consent territory.

```bash
# Recommended: install globally with pnpm
pnpm add -g clawpatch
```

**2. pnpm installed `clawpatch` but it's not on PATH.** pnpm installs global binaries under `$PNPM_HOME` and needs a one-time `pnpm setup` to wire PATH — without it, the install lands but the binary isn't resolvable. (Exact location varies by pnpm version and OS: `~/.local/share/pnpm` on many setups, `$PNPM_HOME/bin/` on others — `pnpm bin -g` reports yours.) Skill detects `pnpm bin -g` exit-0 + `command -v clawpatch` exit non-zero and prints the PNPM_HOME hint:

```bash
pnpm setup            # writes PNPM_HOME + adds it to your shell rc
source ~/.zshrc       # or ~/.bashrc — pick up the new PATH entry
command -v clawpatch  # should now resolve
```

**3. `clawpatch --version` falls outside the tested range.** The skill carries a single-source `SUPPORTED_CLAWPATCH` version range in its prose; see `plugins/flow-next/skills/flow-next-map/SKILL.md` for the current pin. Outside range emits a one-line stderr warning naming expected vs found and continues (degrades — never blocks). Re-pin lands on each clawpatch minor.

**4. Node 20 with `clawpatch` installed.** clawpatch's `engines.node: ">=22"` triggers its own error; the skill propagates it verbatim. Upgrade Node 22+ (e.g. `nvm install 22 && nvm use 22`) or skip `/flow-next:map` — scouts gracefully fall back to the grep/glob path when `.clawpatch/` is absent.

**5. "Should I commit `.clawpatch/` to the repo?"** No — by default the skill writes a `.clawpatch/.gitignore` with `*` + `!.gitignore`, making the feature index local-per-developer. The map is regenerable from `clawpatch map`, the schema may flip between pre-1.0 minor releases, and committing it creates PR review noise + merge conflicts. See [Sharing contract](../skills/flow-next-map/SKILL.md#sharing-contract--local-only-by-design) in the skill prose, or the full trade-off table at [flow-next.dev/skills/map](https://flow-next.dev/skills/map/). Teams that want shared indexes can customize the skeleton — unsupported, but the skill won't clobber a customized `.gitignore` on re-run.

The skill is **opt-in convenience** — `flowctl` core never imports or requires clawpatch; nothing else in flow-next breaks when the skill can't run.

## Uninstall

Run manually in terminal (DCG blocks these from AI agents):

```bash
rm -rf .flow/               # Core flow state
rm -rf scripts/ralph/       # Ralph (if enabled)
```

Or use `/flow-next:uninstall` which cleans up docs and prints commands to run. Doc cleanup removes two independent marker blocks from `CLAUDE.md`/`AGENTS.md`: the `<!-- BEGIN FLOW-NEXT -->` … `<!-- END FLOW-NEXT -->` instructions block and, if `/flow-next:setup` scaffolded one, the `<!-- flow-next:model-routing:start -->` … `<!-- flow-next:model-routing:end -->` model-routing block (removed only when its marker pair is well-formed — a damaged pair is reported and left untouched). `GLOSSARY.md` and `STRATEGY.md` at the repo root are intentionally preserved — they outlive flow-next per the survives-uninstall invariant.

## Renamed skill: `browser` → `flow-next-drive` (1.4.0)

The `browser` skill was renamed `flow-next-drive` in 1.4.0 (surface-aware driver ladder). The invocation is now `/flow-next:flow-next-drive`; the Codex mirror is also `flow-next-drive` (previously `agent-browser`, which collided with the user's global `agent-browser` skill and Codex-native browser skills).

If a cached install still surfaces an orphaned `browser` / `agent-browser` skill after upgrading, it auto-clears within ~7 days as the plugin cache refreshes. To clear it immediately, delete the stale cached marketplace directory under the Claude plugin cache path:

```bash
rm -rf ~/.claude/plugins/cache/<marketplace>   # then reload Claude Code
```

## See also

- [`flowctl.md`](flowctl.md) — full CLI reference (every command, flag, default).
- [`ralph.md`](ralph.md) — Ralph loop internals + DCG setup.
- [`platforms.md`](platforms.md) — platform-specific gotchas (Droid, Codex, OpenCode).
- [`sync-codex.md`](sync-codex.md) — Codex mirror regeneration + validation guards.
