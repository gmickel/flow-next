---
satisfies: [R5]
---

## Description

Ship the 1.1.3 release: docs aligned with new contract (config alias + template discovery cascade + setup-copy step), CHANGELOG entry, manifest version bump 1.1.2 → 1.1.3 across all 5 surfaces via `scripts/bump.sh patch flow-next`.

**Size:** S

**Files:**
- `plugins/flow-next/README.md` (crossSpec docstring + cascade in template section)
- `plugins/flow-next/docs/flowctl.md` (config table row for `planSync.crossSpec`)
- `CLAUDE.md` (discovery cascade in "Creating a spec" — via snippet template since inside BEGIN FLOW-NEXT marker block)
- `agent_docs/local-dev.md` (smoke procedure for opt-in copy step + alias smoke)
- `CHANGELOG.md` (`[flow-next 1.1.3]` entry)
- `.claude-plugin/marketplace.json`, `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json`, README.md badges (via `scripts/bump.sh`)

## Approach

- **`README.md:1589-1594`** — flip the code example to `flowctl config set planSync.crossSpec true`; demote `crossEpic` to footnote ("legacy alias, still readable in 1.x with deprecation warning; removed in 2.0").
- **`docs/flowctl.md:527`** — add new row in the config table: `planSync.crossSpec | bool | false | Cross-spec plan-sync (opt-in)` followed by a footnote `*planSync.crossEpic is the legacy alias; reading it emits a deprecation warning. Removed in 2.0.*`. Match the pipe-delimited shape of existing rows.
- **`CLAUDE.md:120-125`** — discovery cascade documentation. Inside the BEGIN FLOW-NEXT marker block (`:112-140`), so the change must flow through `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md`. Re-setup propagates via the fn-45.3 byte-compare gate at `workflow.md:445-459`.
- **`README.md:513-515`** — add a sentence to the capture/setup section noting the discovery cascade and the opt-in copy step.
- **`agent_docs/local-dev.md`** — add a smoke procedure subsection:
  - Alias smoke: `flowctl config set planSync.crossSpec true && flowctl config get planSync.crossEpic` (expect: stderr deprecation; stdout: `true`).
  - Suppression: `FLOW_NO_DEPRECATION=1 flowctl config get planSync.crossEpic` (expect: silent).
  - Opt-in copy: `/flow-next:setup` in fresh repo → `Copy template / Skip / abort` prompt present.
  - Re-setup gate: customize `SPEC.md`, re-run setup → `Keep mine / Overwrite / abort` prompt.
- **`CHANGELOG.md`** — new `[flow-next 1.1.3]` block above `[flow-next 1.1.2]` (line 5). Sections: `### Added` (planSync.crossSpec canonical key; opt-in repo-root SPEC.md copy step; discovery cascade), `### Deprecated` (planSync.crossEpic; removal in 2.0). Match the 1.1.2 entry style.
- **Version bump:** run `./scripts/bump.sh patch flow-next` to align 5 manifest surfaces (`.claude-plugin/marketplace.json`, `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json`, root README badge, `plugins/flow-next/README.md` badge). The bump.sh script also auto-runs `sync-codex.sh` per fn-45.4 precedent.

## Investigation targets

**Required**:
- `plugins/flow-next/README.md:1589-1594` — crossEpic docstring
- `plugins/flow-next/README.md:513-515` — spec template section
- `plugins/flow-next/docs/flowctl.md:520-540` — config table area
- `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md` — full file (target for CLAUDE.md cascade docs)
- `agent_docs/local-dev.md` — smoke-test section
- `CHANGELOG.md:1-15` — 1.1.2 entry format

**Optional**:
- `scripts/bump.sh` — how the script handles patch bumps; precedent commits (e.g. fn-45.4 release commit, fn-37 / fn-43 patch releases)
- `plugins/flow-next/skills/flow-next-setup/workflow.md:445-459` — fn-45.3 CLAUDE.md byte-compare gate (relevant if CLAUDE.md snippet update triggers re-setup propagation concerns)

## Key context

- Depends on fn-46.1 (alias mechanism shipped) AND fn-46.2 (template cascade + opt-in copy shipped) — confirm both task statuses before authoring docs.
- CLAUDE.md edit goes through the snippet template at `flow-next-setup/templates/claude-md-snippet.md`. Editing CLAUDE.md directly would be overwritten on next setup re-run. The byte-compare gate from fn-45.3 detects user customizations and prompts before clobber.
- Smoke procedure in `agent_docs/local-dev.md` is operator-level (manual probe — `/flow-next:setup` in a real repo). Memory entry `codex-mirror-smoke-docs-miss-composed-2026-05-18` warns: when authoring smoke docs for behavior composed across multiple upstream tasks, inspect the post-sync mirror file directly rather than synthesizing the expected output from spec acceptance criteria alone.
- Version manifests: 1.1.2 → 1.1.3 is patch. The release pattern (per `agent_docs/releasing.md`) is: bump → sync-codex.sh → CHANGELOG → commit → push → tag `flow-next-v1.1.3`. The bump.sh script handles steps 1-2; this task lands the docs + CHANGELOG.

## Acceptance

- [ ] `README.md:1589-1594` flips to `planSync.crossSpec` canonical; legacy `crossEpic` documented as footnote.
- [ ] `docs/flowctl.md:527` gains config-table row for `planSync.crossSpec` with legacy footnote.
- [ ] `CLAUDE.md` discovery cascade documented (via `claude-md-snippet.md` update; CLAUDE.md propagation via byte-compare gate on re-setup).
- [ ] `README.md:513-515` mentions discovery cascade + opt-in copy step.
- [ ] `agent_docs/local-dev.md` gains "Config alias smoke" and "Repo-root SPEC.md smoke" subsections with manual verification steps.
- [ ] `CHANGELOG.md` `[flow-next 1.1.3]` entry above 1.1.2 covering both items (Added: canonical key, opt-in copy, cascade; Deprecated: legacy alias).
- [ ] `./scripts/bump.sh patch flow-next` runs cleanly; 5 manifest surfaces aligned at 1.1.3.
- [ ] `./scripts/sync-codex.sh` re-run after canonical doc edits; mirror clean.
- [ ] Smoke green: 130/130 + standalone rui_refs guard returns no hits.

## Done summary

*Populated by /flow-next:work on completion.*

## Evidence

*Populated by /flow-next:work on completion.*
