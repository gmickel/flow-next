# Local plugin development

How to develop and test plugins from this repo without conflicting with globally-installed versions.

## Uninstall the marketplace versions first

Before running tests or developing plugins locally:

```bash
claude plugins uninstall flow-next
claude plugins uninstall flow
```

Global installs take precedence over `--plugin-dir`, causing tests to use stale cached versions instead of your local changes.

## Preferred: local marketplace install

Hooks fire correctly via `${CLAUDE_PLUGIN_ROOT}`:

```bash
# From this repo root
/plugin marketplace add ./
/plugin install flow-next@flow-next

# Test in any project — plugin hooks work via ${CLAUDE_PLUGIN_ROOT}
```

## Alternative: --plugin-dir (test scripts only)

**Bug #14410:** Plugin hooks don't fire when using `--plugin-dir`. Subagents get `${CLAUDE_PLUGIN_ROOT}` literal instead of expanded path.

Test scripts (`ralph_smoke_test.sh`, `ralph_e2e_rp_test.sh`) handle this by copying hooks to `.claude/hooks/` in the test repo. This workaround is only needed for automated tests using `--plugin-dir`.

See `plans/ralph-e2e-notes.md` for the full setup if needed.

## Smoke tests

```bash
plugins/flow-next/scripts/smoke_test.sh
plugins/flow-next/scripts/ralph_smoke_test.sh
```

**RP smoke** (RP 1.5.68+ auto-opens window with `--create`):
```bash
RP_SMOKE=1 TEST_DIR=/tmp/flow-next-ralph-smoke-rpN KEEP_TEST_DIR=1 \
  plugins/flow-next/scripts/ralph_smoke_rp.sh
```

**Full RP e2e:**
```bash
TEST_DIR=/tmp/flow-next-ralph-e2e-rpN KEEP_TEST_DIR=1 \
  plugins/flow-next/scripts/ralph_e2e_rp_test.sh
```

**Short RP e2e** (2 tasks, faster iteration):
```bash
CREATE=1 TEST_DIR=/tmp/flow-next-ralph-e2e-short-rpN \
  plugins/flow-next/scripts/ralph_e2e_short_rp_test.sh
```

## Codex plain-text prompt smoke

Manual verification that `sync-codex.sh` Stage 3 (fn-45) emits a plain-text numbered-prompt instruction in the Codex mirror — and that the mirror never calls `request_user_input` (Plan-mode-only per openai/codex#10384/#11536/#12694).

Run after any canonical edit that touches an `AskUserQuestion` invocation. Both surfaces — Codex Desktop Default mode AND Codex CLI — must be exercised; behavior is uniform but each path has its own consent-rendering surface.

**Setup once:** install the local marketplace flow-next via Codex (`/plugin marketplace add ./`; `/plugin install flow-next@flow-next`). In a scratch repo seed `.flow/epics/` to trigger the migration consent prompt:

```bash
mkdir -p /tmp/fn-codex-smoke/.flow/epics && cd /tmp/fn-codex-smoke
git init -q
```

**Codex Desktop (Default mode):**
1. Open `/tmp/fn-codex-smoke` in Codex Desktop. Confirm mode shows "Default" (not "Plan").
2. Run `/flow-next:setup`.
3. At the migration consent prompt confirm:
   - Question + 5 numbered options render as plain text in the chat stream (no structured-prompt UI card).
   - The 4 canonical migration options appear first: `1. Migrate now`, `2. Defer`, `3. Suppress permanently`, `4. abort — exit, leave state as-is for review` (per fn-45.2; `abort` is the destructive-action escape hatch).
   - Option `5. Other — type your own answer` appears as the final option (added by the sync-codex.sh fn-45.1 transform; simulates `AskUserQuestion`'s freeform-input affordance).
   - The agent stops and waits for the user reply — does not auto-pick or proceed.
   - No `request_user_input is unavailable in code mode` error surfaces.

**Codex CLI:**
1. `cd /tmp/fn-codex-smoke && codex` (Default mode is the CLI default).
2. Run `/flow-next:setup`.
3. Confirm the same five invariants as Desktop Default mode.

**Post-smoke grep guard** (mirrors R6 sync-codex.sh validation):

```bash
grep -rE '`request_user_input`|request_user_input tool|request_user_input\(|MUST use `request_user_input`|ONLY ask via `request_user_input`' \
  plugins/flow-next/codex/skills/ | grep -v '/templates/'
# Expected: no output
```

Any deviation (structured UI card appears, `request_user_input` error surfaces, agent auto-proceeds without waiting) is a regression — re-run `./scripts/sync-codex.sh` and diff `plugins/flow-next/codex/skills/flow-next-setup/workflow.md` against the canonical to find the missing transform.

## Config alias smoke (planSync.crossEpic → crossSpec)

Manual verification that the fn-46.1 alias mechanism reads + writes the canonical `planSync.crossSpec` key, falls back to the legacy `planSync.crossEpic` on read when the canonical key is absent from the raw config file, and emits a one-line stderr deprecation hint exactly once per process on legacy read.

Run after any change touching `flowctl config get / set` or `_emit_rename_deprecation` (`plugins/flow-next/scripts/flowctl.py`).

**Setup:** scratch repo with `.flow/` initialised.

```bash
mkdir -p /tmp/fn-crossspec-smoke && cd /tmp/fn-crossspec-smoke
.flow/bin/flowctl init   # or run /flow-next:setup once
```

**Canonical write + read:**

```bash
.flow/bin/flowctl config set planSync.crossSpec true
# Expected: writes canonical key only; .flow/config.json contains "crossSpec": true, no "crossEpic" key.

.flow/bin/flowctl config get planSync.crossSpec
# Expected stdout: true   (no deprecation warning on stderr)
```

**Legacy read with deprecation:**

```bash
.flow/bin/flowctl config get planSync.crossEpic
# Expected stdout: true
# Expected stderr: one-line deprecation hint mentioning planSync.crossSpec is the canonical key and crossEpic is removed in 2.0.
```

**Suppression:**

```bash
FLOW_NO_DEPRECATION=1 .flow/bin/flowctl config get planSync.crossEpic
# Expected stdout: true
# Expected stderr: silent (no deprecation hint).
```

**Per-process dedup (warning fires exactly once):**

```bash
# In a single Python process (the dedup cache is per-process), three back-to-back legacy reads:
python3 -c "
import subprocess
for _ in range(3):
    subprocess.run(['.flow/bin/flowctl', 'config', 'get', 'planSync.crossEpic'])
"
# Each subprocess is its own process → warning fires 3 times.
# To verify the per-process dedup contract, invoke the alias path in-process via the flowctl entry point (e.g. via the smoke suite) rather than re-spawning the CLI.
```

Any deviation (canonical `set` touches `crossEpic`, legacy `get` doesn't emit the deprecation, `FLOW_NO_DEPRECATION=1` still emits) is a regression — inspect `cmd_config_get` / `set_config` / `_emit_rename_deprecation` in `flowctl.py`.

## Repo-root SPEC.md smoke (template discovery cascade)

Manual verification that the fn-46.2 cascade walker resolves `<repo_root>/SPEC.md` before `.flow/templates/spec.md`, and that `/flow-next:setup` emits the opt-in copy step (`Copy template / Skip / abort`) on fresh repos + the byte-compare gate (`Keep mine / Overwrite with canonical / abort`) on re-setup with customized content.

Operator-level smoke: requires a real interactive run of `/flow-next:setup`, `/flow-next:capture`, or `/flow-next:interview` in a scratch repo — automation-only verification is insufficient because the consent prompts surface in the agent UI.

**Opt-in copy on fresh repo:**

```bash
mkdir -p /tmp/fn-spec-cascade-smoke && cd /tmp/fn-spec-cascade-smoke
git init -q
# /flow-next:setup
# Expected at Step 4a: prompt renders `Copy template / Skip / abort`.
# Choosing "Copy template" writes <repo_root>/SPEC.md (uppercase) with a top comment noting customization location + the discovery cascade.
```

**Byte-compare gate on re-setup with customized SPEC.md:**

```bash
# Customize the SPEC.md (edit a section header, add a comment line, etc.).
# Re-run /flow-next:setup
# Expected at Step 4a: byte-compare gate detects user edits → prompt renders `Keep mine / Overwrite with canonical / abort`.
# CRLF / trailing-newline normalization: editing on Windows or appending a trailing newline must not trigger a false-positive overwrite.
```

**Cascade hit from repo-root:**

```bash
# With <repo_root>/SPEC.md present (any of the previous steps), run /flow-next:capture or /flow-next:interview on a NEW IDEA.
# Expected: the cascade walker resolves the repo-root file (tier-1 hit) before falling back to .flow/templates/spec.md.
# Add a unique marker comment to SPEC.md (e.g. `<!-- smoke-marker -->`) and verify the spec emitted by capture / interview references the customized scaffold.
```

**Codex Desktop / CLI variant:** the cascade prose is plain markdown and the Codex mirror inherits the same workflow without platform-specific transforms — repeat the steps in Codex Desktop (Default mode) and Codex CLI. Behavior is uniform; the only mirror-specific check is that `/flow-next:setup` renders the consent prompts as the plain-text numbered-prompt fallback per fn-45 (see *Codex plain-text prompt smoke* above).

Some smokes here require manual probing in a real repo (operator-level); deferred where automation cannot exercise an interactive consent prompt. The procedure is captured so future operators can replicate it byte-for-byte.

## RP gotchas (must follow)

- Use `flowctl rp` wrappers only (no direct `rp-cli`).
- Resolve numeric window id via `flowctl rp pick-window --repo-root "$REPO_ROOT"` before builder.
- Do not call `flowctl rp builder` without `--window` and `--summary`.
- Write receipt JSON after chat returns when `REVIEW_RECEIPT_PATH` is set.

## Debug envs (optional, Ralph only)

```bash
FLOW_RALPH_CLAUDE_MODEL=claude-opus-4-6
FLOW_RALPH_CLAUDE_DEBUG=hooks
FLOW_RALPH_CLAUDE_VERBOSE=1
FLOW_RALPH_CLAUDE_PERMISSION_MODE=bypassPermissions
FLOW_RALPH_CLAUDE_NO_SESSION_PERSISTENCE=1
```

## Logs

- Ralph run logs: `scripts/ralph/runs/<run>/`
- Verbose log: `scripts/ralph/runs/<run>/ralph.log`
- Receipts: `scripts/ralph/runs/<run>/receipts/`
- Claude jsonl: `~/.claude/projects/**/<session_id>.jsonl`

## Contributing scope

When planning an epic or opening a PR, include doc updates as acceptance criteria:

- **In scope for any contributor (always):**
  - `CHANGELOG.md` — new entry under the relevant version block
  - `plugins/<plugin>/README.md` — relevant sections + commands/skills tables
  - `CLAUDE.md` — feature description in the relevant subsection
  - `.flow/usage.md` — when listed commands change

- **Maintainer-only (Gordon handles post-merge):**
  - `~/work/mickel.tech/app/apps/flow-next/page.tsx` — feature card on the public marketing site. External contributors **do not** need to update this; lives in a separate private repo. PRs from non-maintainers should skip the website task entirely; Gordon adds the corresponding feature card during release.

Skip rules: pure internal refactors with no user-visible surface skip README + website; bug fixes with no doc impact get a CHANGELOG entry only. When in doubt, include the doc update.
