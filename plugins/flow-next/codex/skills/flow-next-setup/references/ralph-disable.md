# Keep Ralph off

Read only after a supported host's Ralph answer is `No (Recommended)` or the
interactive default resolves to No.

1. Remove only flow-next Ralph guard matcher groups whose nested `command`
 contains `scripts/ralph/hooks/ralph-guard`:
 - Claude Code: `.claude/settings.json`
 - Factory Droid: `.factory/hooks.json` and hooks in
 `.factory/settings.json`
 - Codex: `.codex/hooks.json`
 Preserve all unrelated settings/hooks. Remove an empty `hooks` key. A
 dedicated hooks file containing only Ralph entries may be deleted. Never
 force Codex `[features] hooks = true` while Ralph is off.
2. If `scripts/ralph/` exists, explain that it may include runs/receipts and ask
 before deleting it. Default is keep. A deletion, if explicitly approved,
 may use `rm -rf scripts/ralph/`.
3. Print `Ralph: off (no project guard hooks).`
