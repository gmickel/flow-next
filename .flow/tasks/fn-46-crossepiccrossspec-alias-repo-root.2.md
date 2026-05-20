---
satisfies: [R3, R4]
---

## Description

Implement the spec-template discovery cascade across all consumers (`<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`) and add an opt-in setup step that copies the bundled template to `<repo_root>/SPEC.md`. Re-setup runs use the fn-45.3 byte-compare gate (Keep / Overwrite / abort) with CRLF + trailing-newline normalization added.

**Size:** M

**Files:**
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` (only bash path-resolution site → cascade walker)
- `plugins/flow-next/skills/flow-next-capture/{SKILL.md,workflow.md,phases.md}` (cross-link prose)
- `plugins/flow-next/skills/flow-next-plan/steps.md` (cross-link prose)
- `plugins/flow-next/skills/flow-next-setup/workflow.md` (new opt-in copy step + byte-compare gate)
- `plugins/flow-next/skills/flow-next-setup/templates/{agents-md-snippet.md,claude-md-snippet.md}` (mention cascade)
- `plugins/flow-next/templates/spec.md` (top-comment + drop stale `flow-next-work` from `consumers:` frontmatter)
- `plugins/flow-next/codex/**` (regenerated mirror)

## Approach

- **Cascade walker site (R3):** `flow-next-interview/SKILL.md:639-640` is the only bash path-resolution. Replace the single-path `TEMPLATE_PATH="${CLAUDE_PLUGIN_ROOT:-${DROID_PLUGIN_ROOT}}/templates/spec.md"` with a 4-tier resolver that checks `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled. Use the cascade prose pattern fn-45.3's gate established (numbered list, "first match wins; do not read later paths once a hit is found").
- **Cross-link prose updates:** `capture/SKILL.md:141`, `capture/workflow.md:291`, `capture/phases.md:101,122`, `plan/steps.md:232` — these are documentation cross-links to the bundled template path. Update prose to mention the cascade and that the bundled template is the canonical-source-of-truth, not necessarily the runtime-read path.
- **Snippet templates** (`agents-md-snippet.md:19,26`, `claude-md-snippet.md:19,26`): mention the cascade so downstream users reading CLAUDE.md/AGENTS.md know to put a customized scaffold at `<repo_root>/SPEC.md`.
- **Bundled template** (`plugins/flow-next/templates/spec.md`): drop stale `flow-next-work` entry from `consumers:` frontmatter (lines 3-8) — repo-scout confirmed zero references. Insert a top-comment between line 43 (closing `-->`) and line 45 (`# <spec-id>`) noting customization location: "To customize for your project, copy to `<repo-root>/SPEC.md` and edit there. Discovery cascade: repo-root `SPEC.md` → repo-root `spec.md` → `.flow/templates/spec.md` → bundled."
- **Opt-in setup copy step (R4):** New Step 4c in `flow-next-setup/workflow.md`, immediately after the existing Step 4 template copy at `:145`. Trigger detection via `ls -1 SPEC.md spec.md 2>/dev/null | sort -u | wc -l` (per practice-scout case-insensitive FS recipe). Three outcomes:
  - **0 files:** present a `Copy template / Skip / abort` prompt. On Copy, write `<repo_root>/SPEC.md` from the bundled template. On Skip, the cascade falls through to `.flow/templates/`.
  - **1 file (single hit OR case-insensitive FS resolving both to one):** use whichever exists, no prompt. Treat as "user already has a customized scaffold."
  - **2 files (case-sensitive FS with both distinct):** prefer `SPEC.md`, print a stderr warning ("Both SPEC.md and spec.md exist; preferring uppercase. Unusual setup likely from cross-platform sync.").
- **Byte-compare gate on re-setup** (when SPEC.md exists and diverges): reuse the fn-45.3 three-option pattern from `workflow.md:149-161` (`.flow/usage.md`) and `:445-459` (CLAUDE.md/AGENTS.md). Normalize both sides before compare: strip final `\n`, replace `\r\n` with `\n`. Identical content → no-op (don't bump mtime). Customized → `Keep mine / Overwrite with canonical / abort`.
- **Setup writes uppercase only.** Never write lowercase `spec.md`. The lowercase entry in the cascade is read-only, for users who deliberately created lowercase.
- Run `./scripts/sync-codex.sh` after canonical changes; verify all sync validation guards pass.

## Investigation targets

**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:621-640` — the only bash path-resolution site for the template
- `plugins/flow-next/skills/flow-next-setup/workflow.md:134-161` — Step 4 current template copy + `.flow/usage.md` byte-compare gate (precedent for R4)
- `plugins/flow-next/skills/flow-next-setup/workflow.md:445-459` — CLAUDE.md/AGENTS.md marker-block gate (precedent for R4)
- `plugins/flow-next/templates/spec.md:1-45` — frontmatter + scope-owner comment + header insertion point

**Optional**:
- `plugins/flow-next/skills/flow-next-capture/SKILL.md:141` + `workflow.md:291` + `phases.md:101,122` — cross-link sites
- `plugins/flow-next/skills/flow-next-plan/steps.md:232` — cross-link site
- `plugins/flow-next/skills/flow-next-setup/templates/{agents,claude}-md-snippet.md:19,26` — snippet sites
- `scripts/install-codex.sh:141-155` — top-level templates copy (informational; separate destination, no collision)
- `.flow/memory/bug/build-errors/fn-441-review-cycle-json-contracts-html-2026-05-15.md` — fn-44.1 setup workflow + spec.md template file-copy lessons
- `.flow/memory/bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18.md` — abort-option idempotency from fn-45.2

## Key context

- **Case-insensitive FS collision (macOS APFS, Windows NTFS):** `<repo_root>/SPEC.md` and `<repo_root>/spec.md` resolve to the same inode. `ls -1 SPEC.md spec.md 2>/dev/null | sort -u | wc -l` returns 1 — treat as single hit. On case-sensitive FS (ext4) with both distinct files (count=2), prefer uppercase + warn.
- **Trailing-newline + CRLF normalization** is new for root-level files. `.flow/`-managed files (usage.md, CLAUDE.md marker block) didn't need it because users rarely edit them. `SPEC.md` is explicitly meant for editing — editor variations will add/strip trailing newlines and CRLF on Windows. Compare `content.rstrip(b"\n").replace(b"\r\n", b"\n") == canonical.rstrip(b"\n").replace(b"\r\n", b"\n")`.
- **Discovery cascade prose pattern** must match fn-45.3 gate style: numbered list, explicit "First match wins; do not read later paths once a hit is found." Don't use "check repo-root or .flow/templates" — host agents short-circuit "or"-phrased cascades.
- **Setup wires the new step into Step 4** (file copy concerns together) OR Step 6 (question-driven configuration). Recommend Step 4 placement — keeps file-copy concerns together; the opt-in is a copy decision, not a config setting.
- **The opt-in is "Copy template / Skip / abort"** (not Keep/Overwrite/abort) when no SPEC.md exists — there's nothing existing to keep. Keep/Overwrite/abort fires on re-setup when an existing file diverges. Both prompts are documented in `workflow.md:149-161` precedent.
- **Bundled template `consumers:` frontmatter cleanup:** `flow-next-work` doesn't reference the template (repo-scout confirmed grep returned only an unrelated example path). Drop the stale entry.
- **Codex mirror regenerates the cascade prose** via `sync-codex.sh`. No special transform needed since the cascade prose is plain markdown (no tool-call patterns).
- **install-codex.sh** copies `plugins/flow-next/codex/templates/spec.md` → `~/.codex/templates/spec.md` (Codex global install). The fn-46 opt-in step writes to `<repo_root>/SPEC.md` — different destination, no collision. But the cascade walker should handle Codex installs too: on Codex, `CLAUDE_PLUGIN_ROOT` is empty and `DROID_PLUGIN_ROOT` may be `~/.codex` — bundled-tier resolution likely needs a `${CODEX_HOME:-$HOME/.codex}/templates/spec.md` fallback.

## Acceptance

- [ ] `flow-next-interview/SKILL.md:639-640` cascade walker resolves the template in order: `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`. First match wins.
- [ ] Cross-link prose updated in `capture/{SKILL.md,workflow.md,phases.md}`, `plan/steps.md`, and snippet templates to mention the cascade.
- [ ] Bundled `templates/spec.md` carries a top-comment between line 43-45 noting customization location; `flow-next-work` removed from `consumers:` frontmatter.
- [ ] `flow-next-setup/workflow.md` new Step 4c after `:145` triggers: `ls -1 SPEC.md spec.md 2>/dev/null | sort -u | wc -l` detection; 0 → `Copy template / Skip / abort`; 1 → use existing; 2 → prefer uppercase + stderr warn.
- [ ] On Copy: writes `<repo_root>/SPEC.md` from bundled template; carries the new header comment.
- [ ] Re-setup byte-compare gate: identical content → no-op (no mtime bump); divergence → `Keep mine / Overwrite with canonical / abort`. Both sides normalized via `rstrip(b"\n")` + `replace(b"\r\n", b"\n")` before compare.
- [ ] `./scripts/sync-codex.sh` runs cleanly; all sync validation guards pass; mirror regenerated.
- [ ] Smoke green: `cd /tmp && bash /Users/gordon/work/gmickel-claude-marketplace/plugins/flow-next/scripts/smoke_test.sh` reports 130/130 pass.
- [ ] Sync idempotency confirmed: re-running `./scripts/sync-codex.sh` produces byte-identical mirror.
- [ ] Manual probe (where feasible): create a `<repo_root>/SPEC.md` and confirm `/flow-next:interview --scope=business` on a NEW IDEA reads from it (cascade tier 1 hit).

## Done summary
Implemented 4-tier spec-template discovery cascade (`<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`) at the single bash walker site (`flow-next-interview/SKILL.md:639`). Added `/flow-next:setup` Step 4a opt-in copy: `Copy template / Skip / abort` when no root SPEC.md exists; `Keep mine / Overwrite with canonical / abort` byte-compare gate with CRLF + trailing-newline normalization on re-setup. Cross-link prose in capture/SKILL.md, workflow.md, phases.md, plan/steps.md updated to mention the cascade. Snippet templates (`agents-md-snippet.md`, `claude-md-snippet.md`) updated so downstream CLAUDE.md/AGENTS.md readers know how to customize. Bundled `templates/spec.md` drops stale `flow-next-work` consumer entry + carries new customization-location top-comment. Codex mirror regenerated; smoke 130/130 green; sync idempotency confirmed (byte-identical re-run).
## Evidence
- Commits: 404df420651769bfa03e6c39703c6d645cde48a8
- Tests: cd /tmp && bash plugins/flow-next/scripts/smoke_test.sh (130/130 passed), ./scripts/sync-codex.sh — clean run; all sync validation guards pass, ./scripts/sync-codex.sh — idempotent re-run produces byte-identical output (diff /tmp/sync1.txt /tmp/sync2.txt empty)
- PRs: