# fn-197-copy-less-installs-resolve-flowctl-from.1 Add the plugin-root derivation rung to every flowctl preamble, fix the hardcoded sites, rewrite the Cursor rail

## Description
**What:** Add the probe-proven plugin-root derivation rung (rung 2) to every canonical FLOWCTL preamble, fix the two sites that hard-code `.flow/bin/flowctl`, and rewrite the Cursor guidance rail.

**Details:**
- Insert rung 2 between the env-var probe and the `.flow/bin` fallback at every canonical preamble site (~49: skills' SKILL.md / workflow.md / phases.md / steps.md / references, `agents/quality-auditor.md`, `agents/repo-scout.md`). Exact wording (proven live on Cursor CLI, Cursor app, Grok on 2026-08-14):
  `[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally`
- Fix hardcoded sites: `skills/flow-next-tracker-sync/references/status-sync.md:57` (uses `.flow/bin/flowctl` directly for BRANCH_NAME) and `agents/docs-gap-scout.md:47` (silently degrades to `find` — give it the full chain).
- Rewrite `rules/flow-next.mdc` (Cursor rail): replace its five `.flow/bin/flowctl` invocations and the "if `.flow/bin/flowctl` is not found run setup" remedy with the three-rung chain.
- Regenerate the Codex mirror via `scripts/sync-codex.sh` in the SAME commit. Check the SECTION3C heredoc (~line 359-414) — if `work/phases.md` §3c text changes, update the heredoc in the same commit or the canonical edit is silently dropped. Codex mirror keeps `${CODEX_HOME}` as rung 1; only add rung 2 there if sync patching handles it cleanly (Codex never needs it).
- Before every literal edit: grep `plugins/flow-next/tests/` AND `scripts/sync-codex.sh` for pins; retarget in the same commit, same substance, never weaken.

**Touches:** plugins/flow-next/skills/**, plugins/flow-next/agents/**, plugins/flow-next/rules/**, plugins/flow-next/codex/** (regenerated), scripts/sync-codex.sh, plugins/flow-next/tests/**
## Acceptance
- [ ] Every canonical preamble site carries the three-rung chain in order (env probe → skill-path derivation → `.flow/bin`), byte-identical wording across sites.
- [ ] `status-sync.md:57` and `docs-gap-scout.md:47` no longer reference `.flow/bin/flowctl` without the chain.
- [ ] `rules/flow-next.mdc` teaches the chain; no bare `.flow/bin/flowctl` remedy remains.
- [ ] `scripts/sync-codex.sh` run; mirror regenerated in the same commit; SECTION3C heredoc checked (updated if §3c changed).
- [ ] All test pins on edited literals retargeted in the same commit; full test suite green (exit code captured directly, not piped).
- [ ] Live probe: in a tmp repo with `.flow/` data and no `.flow/bin`, `cursor-agent -p` "list my flow tasks" resolves the installed plugin's flowctl and succeeds.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
