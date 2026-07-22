# Setup modes: plugin vs copy (fn-121)

Contributor-facing map of the dual-mode install system. Read this BEFORE touching the setup skill, the pre-check blocks, the snippet templates, `sync-codex.sh`'s setup transforms, or anything that assumes where flowctl/usage.md/spec.md live. User-facing docs: [`plugins/flow-next/docs/platforms.md`](../plugins/flow-next/docs/platforms.md) "Setup modes".

## Mode taxonomy

| Mode | Stamp (`.flow/meta.json` `setup_mode`) | What exists in the repo | Hosts |
|---|---|---|---|
| **plugin** | `"plugin"` | ONLY the slim CLAUDE.md snippet (marker block). No `.flow/bin/`, no `.flow/templates/spec.md`, no `.flow/usage.md` | Claude Code only |
| **copy** | `"copy"` | Full snapshots: `.flow/bin/flowctl`, `.cmd`, `.py`, `_bootstrap.py`, `-help.txt`; `.flow/templates/spec.md`; `.flow/usage.md` + full snippet | All hosts |
| **legacy/absent** | field missing | Whatever an older setup left | = copy semantics everywhere (pre-checks, uninstall, docs) |

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
3. **Every sync-codex guard pairs with a generation transform.** A guard asserting absence without a transform producing that absence fails every sync. fn-121's pair: the plugin-mode strip transform (setup workflow Step 2b / plugin-Docs variant / Step 7c → copy-only), guarded negatively (no plugin-mode prose in the mirror's setup workflow) and positively (copy path + copy stamp retained; the slim TEMPLATE ships in the mirror on purpose - the retained per-skill pre-check's Refresh-now path reads it cross-host, PR #227 review).
4. **Plugin mode is Claude-Code-only** until bin/ injection is probe-verified elsewhere (Cursor: no env vars, no injection; Codex: `$HOME/.codex/scripts/`; Droid: unverified). Setup never offers the question off Claude Code.
5. **Canonical skill prose never assumes plugin mode.** FLOWCTL preambles stay untouched in every skill; bare `flowctl` appears ONLY in the plugin snippet template, never in skill/agent prose. `which flowctl` failing is still the documented cross-host expectation.

## The pre-check contract (fn-95 mechanism, fn-121 mode-aware)

Carriers: 14 blocking skills (FLOW_SETUP_ASK; 3 bash variants - base, +`mode:autofix`, tracker-sync +`DISPATCH=forked`), 3 notice-only (pilot/land/map), ralph-init EXEMPT. Enforced by `tests/test_precheck_mode_contract.py`.

- `setup_mode == "plugin"` → the version compare is skipped (nothing local to go stale). The block checks the CLAUDE.md sentinel against the expected version; drift emits `FLOW_SNIPPET_ASK` → one consented marker-bounded refresh via the setup-block engine. Suppressed to a stderr note under each variant's autonomy markers (FLOW_RALPH / REVIEW_RECEIPT_PATH / FLOW_AUTONOMOUS / mode tokens) or after a recorded `snippet_ack`.
- copy/absent → the original fn-95 behavior, byte-unchanged.
- ralph-init keeps its version ask in BOTH modes: its `scripts/ralph/` flowctl copies genuinely drift and would otherwise never surface.
- Notice-only carriers wrap their stale notice in `"$SETUP_MODE" != "plugin"`.
- The plugin branch ships in the Codex mirror on purpose: it is inert unless meta says plugin, and it keeps a plugin-mode repo workable for a visiting Codex teammate (Codex preambles self-resolve flowctl from `$HOME/.codex/scripts/`). Cursor CANNOT self-resolve (no env vars) - a Cursor visitor gets the consented convert-to-copy offer in setup instead; setup re-runs on any host route through the mode gate on every pass, including same-version refreshes.

## The commit-point state machine (`flowctl setup-mode set`)

The ONLY writer of `setup_mode`. `copy` stamps unconditionally. `plugin` refuses with an itemized failure list unless the CLAUDE.md rail (block + current sentinel) is present AND every copy artifact is absent — so no prose mistake in the setup skill can produce an invalid plugin stamp. Setup's flow: mode question (Step 2b, consented transition table for leftover artifacts) → snippet write via the engine (Step 7 Docs; CLAUDE.md required, Skip falls back to copy) → stamp LAST (Step 7c). Tested exhaustively in `tests/test_setup_mode_stamp.py`.

## Where things live

- Snippet templates: `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet-plugin.md` (plugin) vs `claude-md-snippet.md` / `agents-md-snippet.md` (copy).
- Canonical usage guide: `plugins/flow-next/templates/usage.md` (moved from the setup-skill templates dir in fn-121; grep gate keeps old-path refs out of active sources).
- Launcher pair: `plugins/flow-next/bin/flowctl` is byte-identical to `scripts/flowctl` except the exec target line (`tests/test_bin_launcher_parity.py`).
- Probe evidence for the whole design (bin PATH injection, pull-rail compliance, zero-setup e2e): fn-121 spec Decision context.
