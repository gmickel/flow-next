---
satisfies: [R3, R4]
---
# fn-186-worktree-kit-non-interactive-cleanup-no.2 Docs: SKILL.md caveats + README/skills.md invocation truth

## Description
R3 - plugins/flow-next/skills/flow-next-worktree-kit/SKILL.md: document the non-interactive cleanup form ('cleanup <name>... --yes'); extend the switch line to note it prints the path and cannot change the caller's shell directory (cd "$(... switch <name>)" idiom); note create sets no upstream so the first push needs --set-upstream/-u. R4 - README.md section '## Commands': fix the opening overclaim 'Every skill is invocable as /flow-next:<name>' to distinguish the 24 slash-command skills from the 5 phrase-triggered ones, and extend the phrase-triggered paragraph to note those are also invocable by full skill name (/flow-next:flow-next-<name>) on hosts that surface skills as commands (verified live on Claude Code). plugins/flow-next/docs/skills.md: same one-line note where the phrase-triggered tier is introduced. Keep prose concise and concrete; plain hyphens only, no em dashes. Do NOT add a commands/ wrapper, do NOT change counts, plugin.json, or the codex catalog.

## Acceptance
R3 and R4 met; no count-pinning test (test_command_shim_flatten, test_chart_docs_inventory, test_chart_skill_contract) breaks; sync-codex.sh idempotent (orchestrator runs it at close-out).

## Done summary
SKILL.md: non-interactive cleanup form, switch prints-a-path + cd idiom, --no-track first-push note. README §Commands overclaim fixed (24 command-backed vs 5 phrase-triggered; full-skill-name invocation noted, verified live on Claude Code); docs/skills.md same note. Codex mirror regenerated (x2, idempotent). Count-pinning suites green.
## Evidence
- Commits: 1fdfc203
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_command_shim_flatten test_chart_docs_inventory test_chart_skill_contract -q
- PRs: