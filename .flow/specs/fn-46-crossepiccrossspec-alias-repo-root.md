# crossEpic→crossSpec alias + repo-root SPEC.md discovery

## Overview

Two small follow-ups bundled in 1.1.3:

1. **Cross-epic config key alias** — `planSync.crossSpec` becomes the canonical key; `planSync.crossEpic` stays readable with a one-line stderr deprecation (suppressed via `FLOW_NO_DEPRECATION=1`), removal in 2.0. Mirrors the fn-43 epic→spec alias pattern, with a critical correctness wrinkle: `flowctl.py` `load_flow_config()` deep-merges defaults, so alias resolution must check **raw file state**, not merged config (a `crossSpec` default of `false` would otherwise mask "user has only set legacy").

2. **Spec template discovery cascade** — `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`. First match wins. `flow-next-setup` gains an opt-in step that copies the bundled template to `<repo_root>/SPEC.md` (uppercase by default); re-setup runs use the fn-45.3 byte-compare gate (Keep / Overwrite / abort) — with CRLF + trailing-newline normalization added since root-level files are explicitly editable.

## Quick commands

```bash
# Alias verification (after Task 1):
.flow/bin/flowctl config set planSync.crossSpec true --json
.flow/bin/flowctl config get planSync.crossEpic --json   # stderr: one-line deprecation; stdout: true
.flow/bin/flowctl config get planSync.crossSpec --json   # stdout: true; no deprecation

# Suppress deprecation:
FLOW_NO_DEPRECATION=1 .flow/bin/flowctl config get planSync.crossEpic --json

# Discovery cascade probe (after Task 2):
# /flow-next:setup in a fresh repo (no SPEC.md) → Copy template / Skip / abort prompt
# /flow-next:setup in a repo with customized SPEC.md → Keep / Overwrite / abort prompt
# /flow-next:capture / interview / plan with repo-root SPEC.md present → uses it over .flow/templates/

# Smoke
bash plugins/flow-next/scripts/smoke_test.sh
./scripts/sync-codex.sh   # regenerate Codex mirror after canonical changes
```

## Boundaries / non-goals

- Not sweeping for other fn-43 leftovers (e.g. `default_sync`, `depends_on_epics` JSON field). Scope is `planSync.crossEpic` only.
- Not removing the `crossEpic` alias in 1.x; removal in 2.0 per fn-43 cadence.
- Not adding a flowctl subcommand for alias logic; handled in-place inside the existing config codepath.
- Not changing the bundled template content; discovery cascade + opt-in copy step only.
- Not auto-creating `<repo_root>/SPEC.md` without user opt-in.
- Not removing the `.flow/templates/spec.md` layer from the cascade; 1.1.0 project-local copy stays as a middle tier.
- Not bumping minor; both items are small adaptations (patch 1.1.2 → 1.1.3).

## Strategy Alignment

Active tracks served by this plan:
- **Cross-platform parity** — keeps Claude / Codex / Droid in lockstep as the config key surface evolves; sync-codex.sh pass propagates the new key.
- **v1.0 vocabulary stability** — completes the fn-43 `epic→spec` rename by closing the last `epic`-named config-key gap; alias + 2.0 removal cadence matches the established convention.

## Decision context

- **Reuse `_emit_rename_deprecation` from fn-43** (`flowctl.py:3865-3888`) — already cached per-process (`_RENAME_DEPRECATION_EMITTED: set[str]`), already honors `FLOW_NO_DEPRECATION=1`. Extend with an optional `extra` parameter to append "Removed in 2.0." if needed, or accept the slight wording divergence.
- **Raw-file alias resolution** — the `load_flow_config()` deep-merge gotcha means alias logic must consult the raw JSON file (or skip defaults for the aliased key). Practice-scout flagged this as a real correctness bug if implemented naively.
- **Cascade order: repo-root → `.flow/templates/` → bundled.** Repo-root matches `STRATEGY.md`/`CLAUDE.md`/`GLOSSARY.md` convention. `.flow/templates/` stays as the post-1.1.0 middle tier so existing setups continue to resolve.
- **Casing rule: SPEC.md preferred, spec.md honored.** On case-insensitive filesystems (macOS APFS, Windows NTFS) the two collide to one inode — treat single hit. On case-sensitive FS with both present, prefer SPEC.md and warn. Setup writes uppercase only.
- **Byte-compare normalization** — root-level files are user-edited; strip trailing `\n` and normalize CRLF→LF before comparing canonical to user content. fn-45.3's gate didn't need this for `.flow/` files; fn-46 adds it for root-level.
- **In-place alias logic in `cmd_config_get`/`set_config`** — no new subcommand. fn-43 precedent (`resolve_spec_arg` at argparse layer) doesn't apply here; this PR establishes the in-config-codepath alias pattern.

## Acceptance

- **R1:** `flowctl config get/set` supports both `planSync.crossSpec` (canonical) and `planSync.crossEpic` (legacy alias). `get` prefers `crossSpec`; falls back to `crossEpic` only when `crossSpec` is **absent from the raw JSON file** (not merely default-valued). `set` writes `crossSpec` and never touches `crossEpic`. Reading the legacy key emits a one-line stderr deprecation via `_emit_rename_deprecation` (suppressed via `FLOW_NO_DEPRECATION=1`). Default in `get_default_config()` switches to `crossSpec: False` (legacy key removed from defaults so its presence in file = explicit legacy set).
- **R2:** `flow-next-setup` workflow writes only the new key on new configs; reads check both with the new key winning. All 5 sites in `flow-next-setup/workflow.md` (lines 237, 268, 309, 415, 497) updated. `agents/plan-sync.md:19` env-var doc references `planSync.crossSpec` as source-of-truth (legacy alias in a footnote).
- **R3:** Spec-template discovery cascade implemented at all consumers: `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`. First match wins. The ONLY bash path-resolution site is `flow-next-interview/SKILL.md:639` — that becomes the cascade walker. Cross-link prose in capture/interview/plan (5 sites) updated to reference the cascade. Snippet templates (`agents-md-snippet.md:19,26`, `claude-md-snippet.md:19,26`) updated to mention repo-root first. `templates/spec.md` `consumers:` frontmatter drops the stale `flow-next-work` entry (repo-scout confirmed zero references).
- **R4:** `flow-next-setup` gains an opt-in step (numbered prompt: `Copy template / Skip / abort`) immediately after the existing `.flow/templates/spec.md` copy at `workflow.md:145`. Triggers when neither `<repo_root>/SPEC.md` nor `<repo_root>/spec.md` exists. Re-setup runs use the fn-45.3 byte-compare gate (`Keep mine / Overwrite with canonical / abort`) — with CRLF → LF normalization and trailing-newline strip before compare. Case-insensitive FS detection via `ls -1 SPEC.md spec.md 2>/dev/null | sort -u | wc -l` per practice-scout. Setup writes uppercase `SPEC.md` only; the file carries a top comment noting customization location and discovery cascade.
- **R5:** Docs + CHANGELOG + version bump: `README.md:1589-1594` flips `crossSpec` to canonical with legacy footnote; `docs/flowctl.md:527` gains config-table row for `planSync.crossSpec` (+ legacy alias footnote); `CLAUDE.md:120-125` documents discovery cascade (via snippet template since the section is inside the BEGIN FLOW-NEXT marker block); `README.md:513-515` adds cascade to capture/setup section; `agent_docs/local-dev.md` gains smoke procedure for the opt-in copy step + alias smoke; `CHANGELOG.md` `[flow-next 1.1.3]` entry covers both items; `scripts/bump.sh patch flow-next` aligns 5 manifest surfaces 1.1.2 → 1.1.3.

## Early proof point

Task `fn-46.1` validates the core alias mechanism: setting `crossSpec`, reading both keys with the new winning, deprecation firing exactly once per process on legacy read, `FLOW_NO_DEPRECATION=1` suppression. If the `load_flow_config()` deep-merge gotcha breaks the legacy-fallback semantic (e.g. `get crossSpec` returns the default `false` and never falls back to `crossEpic`), re-evaluate the raw-file-vs-merged-config strategy before continuing with fn-46.2 (template cascade) and fn-46.3 (docs).

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | flowctl config alias mechanism + deprecation emit + raw-file resolution | fn-46.1 | — |
| R2  | flow-next-setup workflow (5 sites) + plan-sync agent doc | fn-46.1 | — |
| R3  | Spec template discovery cascade (interview bash walker + 5 cross-link sites + snippet templates + bundled-template frontmatter cleanup) | fn-46.2 | — |
| R4  | flow-next-setup opt-in copy step + byte-compare gate with CRLF normalization | fn-46.2 | — |
| R5  | Docs + CHANGELOG 1.1.3 + version bump | fn-46.3 | — |

## References

- `plugins/flow-next/scripts/flowctl.py:1018-1025` — `get_default_config()` defaults dict
- `plugins/flow-next/scripts/flowctl.py:1039-1051` — `load_flow_config()` deep-merge (gotcha source)
- `plugins/flow-next/scripts/flowctl.py:1054-1063` — `get_config(key, default=None)` walker
- `plugins/flow-next/scripts/flowctl.py:1066-1096` — `set_config(key, value)` atomic-writer
- `plugins/flow-next/scripts/flowctl.py:3865-3888` — `_emit_rename_deprecation()` (reuse verbatim)
- `plugins/flow-next/scripts/flowctl.py:4574-4606` — `cmd_config_get` / `cmd_config_set` handlers (extend with alias lookup)
- `plugins/flow-next/skills/flow-next-setup/workflow.md:134-147` — Step 4 current template copy
- `plugins/flow-next/skills/flow-next-setup/workflow.md:149-161` — fn-45.3 `.flow/usage.md` byte-compare gate (precedent for R4)
- `plugins/flow-next/skills/flow-next-setup/workflow.md:237,268,309,415,497` — 5 sites for R2 (note: repo-scout caught the 5th at :497 missing from the spec)
- `plugins/flow-next/skills/flow-next-setup/workflow.md:445-459` — fn-45.3 CLAUDE.md/AGENTS.md marker-block gate
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:639-640` — the only bash path-resolution site for the spec template (target for cascade walker)
- `plugins/flow-next/skills/flow-next-capture/SKILL.md:141`, `workflow.md:291`, `phases.md:101,122` — cross-link sites
- `plugins/flow-next/skills/flow-next-plan/steps.md:232` — cross-link site
- `plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md:19,26` + `claude-md-snippet.md:19,26` — snippet templates referencing `.flow/templates/spec.md` (update to mention cascade)
- `plugins/flow-next/templates/spec.md:1-25` — bundled template frontmatter (drop stale `flow-next-work` from `consumers:`); `:43-45` — header-comment insertion point for customization-location note
- `plugins/flow-next/agents/plan-sync.md:19` — env-var doc site for R2
- `plugins/flow-next/README.md:1589-1594` — `crossSpec` docstring (R5)
- `plugins/flow-next/README.md:513-515` — Spec template capture/setup section (R5 cascade mention)
- `plugins/flow-next/docs/flowctl.md:527` — config table (R5)
- `CLAUDE.md:120-125` — "Creating a spec" guide (R5; via snippet template since inside BEGIN FLOW-NEXT marker)
- `CLAUDE.md:112-140` — BEGIN/END FLOW-NEXT marker block scope
- `agent_docs/local-dev.md` — smoke procedure home (R5)
- `CHANGELOG.md:5` — `[flow-next 1.1.2]` current head; 1.1.3 entry lands above (R5)
- `scripts/install-codex.sh:141-155` — top-level templates copy (no collision; informational)
- Prior art: fn-43 (alias pattern), fn-44 (introduced `.flow/templates/spec.md`), fn-45.3 (byte-compare gate)
- Practice notes: `_emit_rename_deprecation` extension or wording-divergence trade-off; raw-file alias resolution (load_flow_config deep-merge gotcha); SPEC.md/spec.md case-insensitive FS collision (single-canonical-form rule); CRLF + trailing-newline normalization for root-level byte-compare
- Memory entries: `agent-rename-epic-id-prompt-key-changes-2026-05-08` (dispatcher-sweep discipline), `rename-smoke-rewire-variable-form-cli-2026-05-09` (variable-form CLI in smoke), `sync-codexsh-tool-substitution-needs-2026-05-18` (sync-codex.sh pass discipline)
