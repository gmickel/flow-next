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
