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

The plugin ships no hooks.

```bash
# From this repo root
/plugin marketplace add ./
/plugin install flow-next@flow-next
```

## Alternative: --plugin-dir (test scripts only)

**Bug #14410:** Plugin hooks don't fire when using `--plugin-dir`. Subagents get `${CLAUDE_PLUGIN_ROOT}` literal instead of expanded path.

## Smoke tests

```bash
plugins/flow-next/scripts/smoke_test.sh
```

The full CI-run smoke fleet is larger - per-skill suites live beside these in
`plugins/flow-next/scripts/`: `ci_test.sh`, `audit_smoke_test.sh`,
`glossary_smoke_test.sh`, `impl-review_smoke_test.sh`, `make-pr_smoke_test.sh`,
`map_smoke_test.sh`, `prospect_smoke_test.sh`, `resolve-pr_smoke_test.sh`,
`strategy_smoke_test.sh`, `pick_python_test.sh`.
`ls plugins/flow-next/scripts/*_test.sh *_smoke*.sh` is the authoritative list;
this paragraph names the fleet so nobody assumes one suite is the whole gate.

## Codex plain-text prompt smoke

Manual check that `sync-codex.sh` Stage 3 turns each canonical `AskUserQuestion` into a plain-text numbered prompt in the Codex mirror, and that the mirror never calls `request_user_input` (Plan mode only; openai/codex#10384, #11536, #12694).

Run after any canonical edit that touches an `AskUserQuestion` invocation. Exercise both Codex Desktop in Default mode and the Codex CLI: the behaviour is the same, but each renders prompts on its own surface.

The probe is setup's Step 4a `SPEC.md` offer, which asks on any repository with no `SPEC.md` or `spec.md` at its root. **Setup once:** install the local marketplace flow-next in Codex (`/plugin marketplace add ./`, then `/plugin install flow-next@flow-next`). Give each surface its own fresh scratch repository: setup saves the answer in `.flow/meta.json` and does not ask again.

```bash
for d in desktop cli; do mkdir -p "/tmp/fn-codex-smoke-$d" && git -C "/tmp/fn-codex-smoke-$d" init -q; done
```

**Codex Desktop (Default mode):**
1. Open `/tmp/fn-codex-smoke-desktop` in Codex Desktop. Confirm the mode shows "Default" (not "Plan").
2. Run `/flow-next:setup`.
3. At Step 4a confirm:
   - The question and 4 numbered options render as plain text in the chat stream (no structured-prompt UI card).
   - The 3 canonical options come first: `1. Copy template`, `2. Skip`, `3. abort`.
   - `4. Other — type your own answer` is the final option (added by the transform; it stands in for `AskUserQuestion`'s free-text input).
   - The agent stops and waits for the reply; it does not pick an option or proceed.
   - No `request_user_input is unavailable in code mode` error surfaces.
4. Answer `2` (`Skip`, which writes no `SPEC.md`) and let setup finish.

**Codex CLI:**
1. `cd /tmp/fn-codex-smoke-cli && codex` (Default mode is the CLI default).
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
# (`flowctl` here means <plugin-root>/scripts/flowctl, called by path.
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

Operator-level smoke: requires a real interactive run of `/flow-next:setup`, `/flow-next:capture`, or `/flow-next:refine` in a scratch repo — automation-only verification is insufficient because the consent prompts surface in the agent UI.

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
# With <repo_root>/SPEC.md present (any of the previous steps), run /flow-next:capture or /flow-next:refine on a NEW IDEA.
# Expected: the cascade walker resolves the repo-root file (tier-1 hit) before falling back to the bundled template.
# Add a unique marker comment to SPEC.md (e.g. `<!-- smoke-marker -->`) and verify the spec emitted by capture / refine references the customized scaffold.
```

**Codex Desktop / CLI variant:** the cascade prose is plain markdown and the Codex mirror inherits the same workflow without platform-specific transforms — repeat the steps in Codex Desktop (Default mode) and Codex CLI. Behavior is uniform; the only mirror-specific check is that `/flow-next:setup` renders the consent prompts as the plain-text numbered-prompt fallback per fn-45 (see *Codex plain-text prompt smoke* above).

Some smokes here require manual probing in a real repo (operator-level); deferred where automation cannot exercise an interactive consent prompt. The procedure is captured so future operators can replicate it byte-for-byte.

## Logs

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

## Codex installer configuration recovery

`install-codex.sh` preflights its config merge before copying artifacts. Role
registrations are owned by their generated role name plus matching
`config_file = "agents/<name>.toml"`, not by comment markers alone. This repairs
older marker-less registrations and duplicate appended blocks while preserving
unrelated tables and non-conflicting role overrides. A same-name role pointing
to another file, conflicting overrides, or unrelated malformed TOML aborts the
install without replacing the config.

The merger validates the complete result, writes `max_threads` inside `[agents]`,
consolidates the legacy `max_concurrent_threads_per_session` alias,
and atomically replaces the config with its original permissions. Changed
configs retain a private `config.toml.pre-flow-next-*` backup beside the original;
a repeat install leaves an already-current config unchanged. Set `CODEX_HOME`
to repair an alternate profile; do not copy an entire config between machines.
Python 3.11+ is required for TOML validation.
