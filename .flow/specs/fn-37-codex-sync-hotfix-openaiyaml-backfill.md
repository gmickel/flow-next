# Codex sync hotfix — 0.37.1

## Overview

Three silent-degradation gaps in the Codex mirror, all introduced before fn-31 (0.34.0) and never caught:

1. `scripts/sync-codex.sh` `generate_openai_yaml` calls are hard-coded for 9 skills (lines 380-393). Every user-facing slash-command skill added since 0.34.0 (`flow-next-resolve-pr`, `flow-next-prospect`, `flow-next-audit`, `flow-next-memory-migrate`) ships to Codex without UI metadata — raw slugs in the desktop UI, no display name / brand color / default prompt.
2. `flow-next-prime/SKILL.md` (lines 77, 97, 109) + `workflow.md` (lines 194, 196, 306): bare `AskUserQuestion` mandates with no Codex / Droid variants.
3. `flow-next-setup/workflow.md` (line 316): same bare mandate.

CLAUDE.md gains a cross-platform table extension and an "Adding a new user-facing skill" checklist so future skill additions can't repeat this.

Patch bump (0.37.0 → 0.37.1) — pure tech-debt cleanup.

## Acceptance criteria

- **R1:** `scripts/sync-codex.sh` adds `generate_openai_yaml` calls for `flow-next-resolve-pr`, `flow-next-prospect`, `flow-next-audit`, `flow-next-memory-migrate`. Workflow color (#3B82F6) for the agent-native skills (audit/prospect/memory-migrate); review-leaning red (#EF4444) for resolve-pr.
- **R2:** Validation block in `sync-codex.sh` extended: instead of `>= 9 openai.yaml files`, validate against an explicit list of REQUIRED skills (named) — script fails CI when a future user-facing skill is added without an entry.
- **R3:** `flow-next-prime/SKILL.md` + `workflow.md` bare `AskUserQuestion` mandates extended with cross-platform variants (mirror `flow-next-audit/SKILL.md:62` exactly): Claude `AskUserQuestion` (with `ToolSearch select:AskUserQuestion` schema-load fallback) / Codex `request_user_input` / Gemini-Droid-Pi `ask_user` / numbered-options-in-text last-resort fallback.
- **R4:** `flow-next-setup/workflow.md` line 316 extended with same cross-platform variants.
- **R5:** `CLAUDE.md` `## Cross-platform patterns (Claude Code + Factory Droid)` section extended: blocking-question tool row + subagent dispatch row (the existing table covers var refs, hook matchers, agent permissions, plugin paths — extend with the two missing rows).
- **R6:** `CLAUDE.md` adds new `### Adding a new user-facing skill` checklist (under Cross-platform patterns section). Concrete steps the next skill author MUST follow: canonical skill mentions cross-platform variants inline; `generate_openai_yaml` entry in sync-codex.sh; validation list updated; sync-codex.sh re-run; commands list updated in CLAUDE.md / README.md / website.
- **R7:** `./scripts/sync-codex.sh` re-run; Codex mirror regenerated; validation passes (no errors); all 13 user-facing skills have `agents/openai.yaml` files.
- **R8:** Smoke verification: assert `find plugins/flow-next/codex/skills -name openai.yaml | wc -l` returns >= 13. Each `openai.yaml` has `interface:` + `policy:` keys + valid YAML.
- **R9:** `./scripts/bump.sh patch flow-next` runs cleanly; manifests at 0.37.1 across `.claude-plugin/marketplace.json`, `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json`.
- **R10:** `CHANGELOG.md` `[flow-next 0.37.1]` block above 0.37.0 with `### Fixed` covering: openai.yaml backfill (4 skills), cross-platform AskUserQuestion variants in prime/setup, CLAUDE.md cross-platform table extension + adding-new-skill checklist.
- **R11:** All existing smoke tests still green: `audit_smoke_test.sh`, `smoke_test.sh`, `prospect_smoke_test.sh`, `ralph_smoke_test.sh`.
- **R12:** No website update needed (no user-visible feature change — pure infra/Codex polish).

## Boundaries

- Not changing skill behavior. Cross-platform extensions only add to existing language; no new flags, no new questions, no new tools used.
- Not bumping minor. Tech-debt cleanup is patch.
- Not touching `flow-next-interview` (covered by fn-36 task 2).
- Not introducing plain-text mode opt-out. Existing `mode:autofix` / `--yes` / `--fix-all` are sufficient (per earlier discussion — interview/setup/audit/migrate questions are dynamic, not predictable, so blocking tools are right where they're used).
- Not adding openai.yaml for the helper skills (deps, export-context, sync, ralph-init, worktree-kit, rp-explorer, browser). Those are slash-command-internal or developer-facing; can be added later if/when Codex desktop renders them.
