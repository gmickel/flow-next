# Setup modes: plugin vs copy (fn-121)

Contributor-facing map of the dual-mode install system. Read this BEFORE touching the setup skill, the pre-check blocks, the snippet templates, `sync-codex.sh`'s setup transforms, or anything that assumes where flowctl/usage.md/spec.md live. User-facing docs: [`plugins/flow-next/docs/platforms.md`](../plugins/flow-next/docs/platforms.md) "Setup modes".

## Mode taxonomy

| Mode | Stamp (`.flow/meta.json` `setup_mode`) | What exists in the repo | Hosts |
|---|---|---|---|
| **plugin** | `"plugin"` | ONLY the slim CLAUDE.md snippet (marker block). No `.flow/bin/`, no `.flow/templates/spec.md`, no `.flow/usage.md` | Claude Code only |
| **copy** | `"copy"` | Full snapshots: `.flow/bin/flowctl`, `.cmd`, `.py`, `_bootstrap.py`, `-help.txt`; `.flow/templates/spec.md`; `.flow/usage.md` + full snippet | All hosts |
| **legacy/absent** | field missing | Whatever an older setup left | = copy semantics for artifact resolution, uninstall, and docs |

## Per-artifact resolution chains

| Artifact | Plugin mode | Copy mode |
|---|---|---|
| flowctl (skills) | `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl` → `.flow/bin/flowctl` — the FLOWCTL preamble, UNCHANGED by fn-121 | same preamble; `.flow/bin` rung is the one that matters for plugin-less consumers |
| flowctl (plain Bash, no skill) | bare `flowctl` — Claude Code injects `<plugin>/bin/` onto the Bash PATH (`plugins/flow-next/bin/flowctl` resolves the tracked bootstrap/source under `../scripts/`) | `.flow/bin/flowctl` |
| Usage guide | `flowctl usage` → bundled `plugins/flow-next/templates/usage.md` (canonical location since fn-121) | same command falls back to `.flow/usage.md`; also readable on disk |
| Spec template | 4-tier cascade bottoms out at the bundled `${PLUGIN_ROOT}/templates/spec.md` | cascade hits `.flow/templates/spec.md` first |
| Agent rail | slim snippet (`claude-md-snippet-plugin.md`) in CLAUDE.md — trigger-shaped `flowctl usage` pull directives | full snippet (`claude-md-snippet.md` / `agents-md-snippet.md`) with `.flow/bin` paths |

## Invariants (violating any of these is a review blocker)

1. **No silent writes to tracked repo files, ever.** The rejected fn-96 design (silent snapshot refresh) stays dead. Every mode switch, artifact cleanup, or snippet refresh is consented (AskUserQuestion) and marker-bounded.
2. **Setup-block markers are EXACT strings.** The engine (`flowctl setup-block apply/resolve`) matches the standalone lines `<!-- BEGIN FLOW-NEXT -->` / `<!-- END FLOW-NEXT -->`. Never parameterize the marker; the snippet schema version is the INTERNAL sentinel line `<!-- flow-next:snippet:vN -->` (first line inside the block). Expected N = `SNIPPET_SCHEMA_VERSION` in flowctl.py; bump it ONLY on a genuine snippet-contract change (it re-arms one consented refresh ask per repo).
3. **Every sync-codex guard pairs with a generation transform.** A guard asserting absence without a transform producing that absence fails every sync. fn-121's pair: the plugin-mode strip transform (setup workflow Step 2b / plugin-Docs variant / Step 7c → copy-only), guarded negatively (no plugin-mode prose in the mirror's setup workflow) and positively (copy path + copy stamp retained; the slim template ships in the mirror on purpose for a visiting Codex teammate in a plugin-mode repo).
4. **Plugin mode is Claude-Code-only** until bin/ injection is probe-verified elsewhere (Cursor: no env vars, no injection; Codex: `$HOME/.codex/scripts/`; Droid: unverified). Setup never offers the question off Claude Code.
5. **Canonical skill prose never assumes plugin mode.** FLOWCTL preambles stay untouched in every skill; bare `flowctl` appears ONLY in the plugin snippet template, never in skill/agent prose. `which flowctl` failing is still the documented cross-host expectation.

## Copy-mode version drift

Plan is the sole lifecycle consumer of `setup_version`. When copy-mode metadata and the installed plugin version are both available and differ, interactive Plan offers **Refresh now (Recommended)** or **Continue this run**. Refresh stops and directs the user to run `/flow-next:setup`, then rerun Plan; autonomous, Ralph, and receipt-driven invocations warn once and continue. Match, plugin mode, and unavailable comparison evidence are silent. Direct invocation of other skills performs no version preflight.

Setup remains the sole owner of setup-mode transitions, snippet integrity, setup-version stamping, and marker-bounded refresh. Legacy `version_ack` / `snippet_ack` fields are tolerated as unknown metadata but are neither read nor written by lifecycle skills. `tests/test_precheck_mode_contract.py` locks this division of responsibility across canonical and Codex paths.

## The commit-point state machine (`flowctl setup-mode set`)

The ONLY writer of `setup_mode`. `copy` stamps unconditionally. `plugin` refuses with an itemized failure list unless the CLAUDE.md rail (block + current sentinel) is present AND every copy artifact is absent — so no prose mistake in the setup skill can produce an invalid plugin stamp. Setup's flow: mode question (Step 2b, consented transition table for leftover artifacts) → snippet write via the engine (Step 7 Docs; CLAUDE.md required, Skip falls back to copy) → stamp LAST (Step 7c). Tested exhaustively in `tests/test_setup_mode_stamp.py`.

## Where things live

- Snippet templates: `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet-plugin.md` (plugin) vs `claude-md-snippet.md` / `agents-md-snippet.md` (copy).
- Canonical usage guide: `plugins/flow-next/templates/usage.md` (moved from the setup-skill templates dir in fn-121; grep gate keeps old-path refs out of active sources).
- Launcher pair: `plugins/flow-next/bin/flowctl` is byte-identical to `scripts/flowctl` except the exec target line (`tests/test_bin_launcher_parity.py`).
- Probe evidence for the whole design (bin PATH injection, pull-rail compliance, zero-setup e2e): fn-121 spec Decision context.
