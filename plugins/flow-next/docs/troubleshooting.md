# Troubleshooting

Common recovery patterns for stuck tasks, broken state, Ralph debugging, and review-backend conflicts. For deeper subsystem guides see [`flowctl.md`](flowctl.md) (CLI reference), [`ralph.md`](ralph.md) (Ralph internals), and the parent [`../README.md`](../README.md).

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

## Custom rp-cli instructions conflicting

> **Caution**: If you have custom instructions for `rp-cli` in your `CLAUDE.md` or `AGENTS.md`, they may conflict with Flow-Next's RepoPrompt integration.

Flow-Next's plan-review and impl-review skills include specific instructions for `rp-cli` usage (window selection, builder workflow, chat commands). Custom rp-cli instructions can override these and cause unexpected behavior.

**Symptoms:**
- Reviews not using the correct RepoPrompt window
- Builder not selecting expected files
- Chat commands failing or behaving differently

**Fix:** Remove or comment out custom rp-cli instructions from your `CLAUDE.md`/`AGENTS.md` when using Flow-Next reviews. The plugin provides complete rp-cli guidance.

## Copilot review backend fails on Windows with "command line too long"

> **Caution**: Copilot CLI on Windows cannot accept spec-sized review prompts. WSL is the only known workaround.

Spec-driven `flowctl copilot impl-review` / `plan-review` / `completion-review` calls on native Windows fail with a clean error from flow-next 1.1.8+:

```
copilot -p failed: Copilot review cannot run on Windows: projected command
line is 53,210 chars (prompt alone is 51,847 chars), exceeding the Windows
CreateProcessW cap of 32,767 chars. ...
```

**Root cause:** Windows `CreateProcessW` caps the full command line at 32,767 chars. Copilot CLI (1.0.51 as of 2026-05) offers no off-argv prompt delivery — no `--prompt-file`, no `@file`, no stdin — so flow-next must pass the full review prompt through `-p "<text>"`. Spec-sized prompts blow the cap. The temp-file staging in `run_copilot_exec` is a hygiene scratch buffer, not an alternate delivery path.

**Pre-1.1.8 symptom:** the same condition surfaced as an opaque `OSError winerror 206` or `[WinError 206] The filename or extension is too long`.

**Workaround:** Run flowctl from WSL. The Linux argv limit (~2 MB) absorbs spec-sized prompts comfortably. Copilot CLI runs unmodified inside WSL.

**Permanent fix:** lives in Copilot CLI upstream — tracking [github/copilot-cli#3398](https://github.com/github/copilot-cli/issues/3398) (request for first-class `--prompt-file` support).

## Uninstall

Run manually in terminal (DCG blocks these from AI agents):

```bash
rm -rf .flow/               # Core flow state
rm -rf scripts/ralph/       # Ralph (if enabled)
```

Or use `/flow-next:uninstall` which cleans up docs and prints commands to run. `GLOSSARY.md` and `STRATEGY.md` at the repo root are intentionally preserved — they outlive flow-next per the survives-uninstall invariant.

## See also

- [`flowctl.md`](flowctl.md) — full CLI reference (every command, flag, default).
- [`ralph.md`](ralph.md) — Ralph loop internals + DCG setup.
- [`platforms.md`](platforms.md) — platform-specific gotchas (Droid, Codex, OpenCode).
- [`sync-codex.md`](sync-codex.md) — Codex mirror regeneration + validation guards.
