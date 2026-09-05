# Setup: one copy-less mode (fn-197)

Contributor-facing map of the install system. Read this BEFORE touching the setup skill, the pre-check blocks, the snippet templates, `sync-codex.sh`'s setup transforms, or anything that assumes where flowctl / the usage guide / the spec template live. User-facing docs: [`plugins/flow-next/docs/platforms.md`](../plugins/flow-next/docs/platforms.md) "What setup does".

## One mode: nothing is copied into the repo

`/flow-next:setup` has a single mode on every host. It runs `flowctl init`, writes the versioned docs-snippet block, walks the config ceremony, and optionally seeds **user-owned** files (`SPEC.md`, `.flow/criteria.md`, `.codex/agents/*.toml` on Codex, Ralph). It never writes `.flow/bin/`, `.flow/templates/spec.md`, or `.flow/usage.md`.

Repos set up before fn-197 carry those snapshots. They are inert: nothing reads them, deleting them changes nothing observable. Setup (unconditional offer) and `/flow-next:plan` (one-line nudge) both detect them from flowctl's `LEGACY_COPY_ARTIFACTS` list and offer deletion — never silently. Old `setup_mode` / `setup_version` stamps in `.flow/meta.json` are tolerated as inert metadata and never read.

## Per-artifact resolution

| Artifact | How it resolves |
|---|---|
| flowctl (skills) | The three-rung FLOWCTL preamble: `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl` → the plugin root derived as the directory two levels above the loading skill's own SKILL.md (Cursor, Grok) → `.flow/bin/flowctl` as a silent legacy backstop. The Codex mirror's rung 1 is `${CODEX_HOME:-$HOME/.codex}/scripts/flowctl`. |
| flowctl (plain Bash, no skill) | Bare `flowctl` where the host injects the plugin's `bin/` onto PATH (Claude Code); otherwise call the plugin's `scripts/flowctl` by path. |
| Usage guide | `flowctl usage` → bundled `plugins/flow-next/templates/usage.md`. A repo-local `.flow/usage.md` is honored only as inert legacy grace. |
| Spec template | 3-tier cascade: `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`. |
| Agent rail | The versioned docs snippet (`claude-md-snippet.md` / `agents-md-snippet.md`) inside the `FLOW-NEXT` marker block, with trigger-shaped `flowctl usage` pull directives. |

## Invariants (violating any of these is a review blocker)

1. **Preserve ownership and prior consent.** The rejected fn-96 design (silent snapshot refresh) stays dead. Setup-block may refresh a block proven pristine from its recorded hash; a customized or hash-absent differing block requires the documented Keep / Overwrite / abort decision. Reuse authorization already given for the same action. Changes stay marker-bounded. Deleting leftover artifacts requires explicit authorization; never infer deletion from a setup invocation.
2. **Setup-block markers are derived, deterministically, from the block id (fn-171).** `flowctl setup-block apply/resolve/check` all take an optional `--id <BLOCK-ID>`; the default id `FLOW-NEXT` derives exactly the historical markers `<!-- BEGIN FLOW-NEXT -->` / `<!-- END FLOW-NEXT -->` (omitting `--id` and passing `--id FLOW-NEXT` are byte-identical - same markers, same state key). A custom id derives its own pair, `<!-- BEGIN <ID> -->` / `<!-- END <ID> -->`, scoped independently of every other id's markers in the same file. Free-form `--begin`/`--end` marker overrides remain forbidden - ids are the only parameterization surface, so the marker↔state-key relationship stays 1:1 and the setup skill's own `FLOW-NEXT` call sites keep their exact strings. The snippet schema version is a separate, unrelated concern: the INTERNAL sentinel line `<!-- flow-next:snippet:vN -->` (first line inside the block). Expected N = `SNIPPET_SCHEMA_VERSION` in flowctl.py; bump it ONLY on a genuine snippet-contract change (it re-arms one consented refresh ask per repo). **A bump is the only thing that makes a user re-run setup** — say so in the changelog's upgrade-actions block.
3. **Pristine state is keyed per `(path, id)`.** `meta.json`'s `setup.block_hashes` is a nested `{<path>: {<id>: <hash-or-sentinel>}}` map, so several independently-tracked blocks can live in one file without clobbering each other's recorded state. A pre-fn-171 install's flat `{<path>: <hash>}` entries are read transparently as the default id's hash and upgraded to the nested form on first write - no separate migration step, and existing single-block callers see no behavior change.
4. **Setup writes nothing into `.flow/` except state flowctl owns.** A setup (or `flowctl init`) run that created `.flow/bin/`, `.flow/templates/spec.md`, or `.flow/usage.md` has broken this. There is no mode in which copying is correct.
5. **Skill prose resolves flowctl through the three-rung chain — bare `flowctl` is not a substitute.** This inverts fn-121's rule. Bare `flowctl` is fine in the *docs snippet* (Claude Code's PATH injection makes it true there) and in plain-Bash examples aimed at a human, but a skill's own preamble spells all three rungs, in order, verbatim. Do **not** "simplify" it to one rung, and do **not** re-add a copy step to make rung 3 reachable: rung 3 is a silent backstop for repos mid-migration, never something setup produces.
6. **Every sync-codex guard pairs with a generation transform.** A guard asserting absence without a transform producing that absence fails every sync, and vice versa. Remove them together.

## Where things live

- Snippet templates: `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md` / `agents-md-snippet.md` / `model-routing-snippet.md`.
- Canonical usage guide: `plugins/flow-next/templates/usage.md`; `flowctl usage` resolution is covered by `tests/test_cmd_usage.py`.
- Canonical spec scaffold: `plugins/flow-next/templates/spec.md`; the resolution walker is single-sourced in `plugins/flow-next/references/spec-template-discovery.md`.
- Legacy-artifact list (the single source both cleanup touchpoints read): `LEGACY_COPY_ARTIFACTS` in `plugins/flow-next/scripts/flowctl.py`.
- Launcher pair: `plugins/flow-next/bin/flowctl` is byte-identical to `scripts/flowctl` except the exec target line (`tests/test_bin_launcher_parity.py`); `scripts/flowctl.cmd` is the cmd.exe / PowerShell sibling.
- Lifecycle-skill division of responsibility (setup owns snippet integrity and stamping; plan performs no version preflight): `tests/test_precheck_mode_contract.py`.
- Probe evidence for the resolution chain (skill-path derivation on Cursor + Grok, zero-`.flow/bin` e2e): fn-197 spec Evidence.

## This repository's developer entry points

Root `AGENTS.md` and `CLAUDE.md` are independent ordinary files. Both require
`agent_docs/project.md`, which owns shared development policy. Their marker
blocks are customized project content; treat each `(path, FLOW-NEXT)` identity
independently and preserve customized-state handling. Repo-specific gate,
receipt, and release rules belong outside the replaceable snippet. This local
arrangement does not change the templates shipped to other repositories.
