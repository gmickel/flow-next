# Local plugin development

How to develop and test plugins from this repo without conflicting with globally-installed versions.

## Resolve installed-plugin precedence when testing local loading

Source inspection and ordinary unit tests do not require uninstalling plugins.
When an explicitly selected integration/dogfood setup loads a cached marketplace
copy instead of the local source, inspect the active plugin origin first. If
uninstalling that conflicting copy is needed, make the intended installation
change explicit before using:

```bash
claude plugins uninstall flow-next
claude plugins uninstall flow
```

A conflicting global install can cause a loader test to exercise cached source.
Verify which copy the test actually loads; use an isolated test installation
where practical. The commands above are remediation, not a prerequisite for
every development task.

## Preferred: local marketplace install

Hooks are PROJECT-level since fn-114 (ralph-init merges them into .claude/settings.json; the plugin ships none). To verify they fire:

```bash
# From this repo root
/plugin marketplace add ./
/plugin install flow-next@flow-next

# Test in a project where ralph-init has registered the guard hooks
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

The full CI-run smoke fleet is larger - per-skill suites live beside these in
`plugins/flow-next/scripts/`: `ci_test.sh`, `audit_smoke_test.sh`,
`glossary_smoke_test.sh`, `impl-review_smoke_test.sh`, `make-pr_smoke_test.sh`,
`map_smoke_test.sh`, `prospect_smoke_test.sh`, `resolve-pr_smoke_test.sh`,
`strategy_smoke_test.sh`, `plan_review_prompt_smoke.sh`, `pick_python_test.sh`.
`ls plugins/flow-next/scripts/*_test.sh *_smoke*.sh` is the authoritative list;
this paragraph names the fleet so nobody assumes two suites is the whole gate.

Non-RP Ralph e2e (real `claude`, no RepoPrompt): `plugins/flow-next/scripts/ralph_e2e_test.sh` (run from a non-plugin repo dir; sets its own `TEST_DIR`).

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

## Config alias removal smoke (planSync.crossEpic removed in 2.0.0)

The fn-46.1 legacy alias (`planSync.crossEpic` → `planSync.crossSpec`, deprecated 1.1.3+) was removed in 2.0.0 per the documented 1.x deprecation promise. Manual verification that the removal holds: flowctl reads + writes only the canonical `planSync.crossSpec` key, a leftover `crossEpic` key in the raw config file is inert (no read fallback, no init mirror), and no deprecation hint fires.

Run after any change touching `flowctl config get / set`, `cmd_init`'s config upgrade, or `_CONFIG_KEY_ALIASES` (`plugins/flow-next/scripts/flowctl.py`). The automated counterparts are `tests/test_config_alias.py` + `tests/test_init_crossspec_mirror.py`.

**Setup:** scratch repo with `.flow/` initialised.

```bash
mkdir -p /tmp/fn-crossspec-smoke && cd /tmp/fn-crossspec-smoke
flowctl init   # or run /flow-next:setup once
# (`flowctl` is the plugin's own launcher — bare on Claude Code via plugin bin/
#  PATH injection, otherwise call <plugin-root>/scripts/flowctl by path.
#  Nothing is copied into the repo.)
```

**Canonical write + read:**

```bash
flowctl config set planSync.crossSpec true
# Expected: writes canonical key only; .flow/config.json contains "crossSpec": true, no "crossEpic" key.

flowctl config get planSync.crossSpec
# Expected stdout: true   (nothing on stderr)
```

**Leftover legacy key is inert (no fallback, no mirror, no warning):**

```bash
# Seed a pre-2.0 layout: legacy key only, canonical absent.
python3 -c "
import json, pathlib
p = pathlib.Path('.flow/config.json')
cfg = json.loads(p.read_text())
cfg['planSync'] = {'crossEpic': True}
p.write_text(json.dumps(cfg, indent=2))
"

flowctl config get planSync.crossSpec --raw --json
# Expected: "value": null — the canonical read must NOT fall back to the legacy value.

flowctl config get planSync.crossSpec
# Expected stdout: false (the default) — not the legacy true. Nothing on stderr.

flowctl init
# Expected: NO "mirrored legacy planSync.crossEpic" action; crossSpec lands at the
# default false; the leftover crossEpic key is preserved but never read.
```

Any deviation (canonical `get` surfaces the legacy value, `init` mirrors `crossEpic` → `crossSpec`, or any `planSync.crossEpic` deprecation hint appears on stderr) is a regression — inspect `_CONFIG_KEY_ALIASES` / `cmd_config_get` / `cmd_init` in `flowctl.py`.

## Repo-root SPEC.md smoke (template discovery cascade)

Manual verification that the fn-46.2 cascade walker resolves `<repo_root>/SPEC.md` before the bundled `${PLUGIN_ROOT}/templates/spec.md`, and that `/flow-next:setup` emits the opt-in copy step (`Copy template / Skip / abort`) on fresh repos + the byte-compare gate (`Keep mine / Overwrite with canonical / abort`) on re-setup with customized content.

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
# Expected: the cascade walker resolves the repo-root file (tier-1 hit) before falling back to the bundled template.
# Add a unique marker comment to SPEC.md (e.g. `<!-- smoke-marker -->`) and verify the spec emitted by capture / interview references the customized scaffold.
```

**Codex Desktop / CLI variant:** the cascade prose is plain markdown and the Codex mirror inherits the same workflow without platform-specific transforms — repeat the steps in Codex Desktop (Default mode) and Codex CLI. Behavior is uniform; the only mirror-specific check is that `/flow-next:setup` renders the consent prompts as the plain-text numbered-prompt fallback per fn-45 (see *Codex plain-text prompt smoke* above).

Some smokes here require manual probing in a real repo (operator-level); deferred where automation cannot exercise an interactive consent prompt. The procedure is captured so future operators can replicate it byte-for-byte.

## RP gotchas (must follow)

- Use `flowctl rp` wrappers only (no direct RepoPrompt CLI calls).
- Initialize CE review state once with `flowctl rp setup-review --repo-root "$REPO_ROOT" --summary "$SUMMARY" --response-type review --response-file "$RESPONSE_FILE" --create > "$SETUP_FILE"`. Source the setup file in each fresh shell block.
- CE validates and consumes the direct `context_builder` result (prompt, formatted selection, positive file/token counts, context/chat identity, and terminal review response). Do not inspect a visible compose tab, augment selection, or send a second initial chat. Classic alone uses the returned `W`/`T` with the legacy selection/chat wrappers.
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
  - root `README.md` § Commands table + `plugins/flow-next/docs/skills.md` — the command/skill surfaces (`plugins/flow-next/README.md` is a thin pointer stub, no tables)
  - `CLAUDE.md` — feature description in the relevant subsection
  - `plugins/flow-next/templates/usage.md` — when listed commands change (the single source `flowctl usage` prints)

- **Maintainer-only (Gordon handles post-merge):**
  - `~/work/mickel.tech/app/apps/flow-next/page.tsx` — feature card on the public marketing site. External contributors **do not** need to update this; lives in a separate private repo. PRs from non-maintainers should skip the website task entirely; Gordon adds the corresponding feature card during release.

Skip rules: pure internal refactors with no user-visible surface skip README + website; bug fixes with no doc impact get a CHANGELOG entry only. When in doubt, include the doc update.
