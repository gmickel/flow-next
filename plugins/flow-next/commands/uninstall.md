---
name: uninstall
description: Remove flow-next files from project
---

# Flow-Next Uninstall

Use `AskUserQuestion` to confirm:

**Question 1:** "Remove flow-next from this project?"
- "Yes, uninstall"
- "Cancel"

If cancel → stop.

**Question 2:** "Keep your .flow/ tasks and specs?"
- "Yes, keep tasks" → partial uninstall
- "No, remove everything" → full uninstall

## Generate removal instructions

Based on answers, generate the appropriate commands and print them for the user to run manually.

**If keeping tasks:**

Copy-mode repos (`setup_mode` absent or `"copy"` in `.flow/meta.json`):
```
To complete uninstall, run these commands manually:

rm -rf .flow/bin .flow/templates .flow/usage.md
```

Plugin-mode repos (`setup_mode: "plugin"`): there are no `.flow/bin`, `.flow/templates`, or `.flow/usage.md` copies to remove. Instead, remove the `<!-- BEGIN FLOW-NEXT -->`...`<!-- END FLOW-NEXT -->` block from CLAUDE.md and strip the stamps from `.flow/meta.json` (`setup_mode`, `setup_version`, `version_ack`, `snippet_ack`).

**If removing everything:**
```
To complete uninstall, run these commands manually:

rm -rf .flow
```

**Always check for Ralph and add if exists:**
```bash
# Check if Ralph is installed
if [[ -d scripts/ralph ]]; then
  echo "rm -rf scripts/ralph"
fi
```

## Remove Ralph guard hook entries (AI can do this)

Plugin installs no longer ship hooks. Any Ralph guard entries live in **project** settings, registered by `/flow-next:ralph-init`. Strip them the same way setup does on "No":

**Fingerprint:** nested hook `command` contains `scripts/ralph/hooks/ralph-guard`.

For each path that exists, Read then Edit (never clobber unrelated hooks; if the file becomes empty hooks-only, delete the file or remove the empty `hooks` key):

| Host | Path |
|---|---|
| Claude Code / Grok | `.claude/settings.json` (`hooks` key) |
| Factory Droid | `.factory/hooks.json` (primary); also strip under `.factory/settings.json` `hooks` if present |
| Codex | `.codex/hooks.json` |

Do **not** introduce a flowctl hook-remove command. Agent-driven Read+Edit only.

## Clean up docs (AI can do this)

For CLAUDE.md and AGENTS.md: if file exists, remove everything between `<!-- BEGIN FLOW-NEXT -->` and `<!-- END FLOW-NEXT -->` (inclusive). This is safe for the AI to execute.

**Also remove the optional model-routing scaffold block** (written by `/flow-next:setup`) from the same files. It is a *second*, independent marker pair: `<!-- flow-next:model-routing:start -->` … `<!-- flow-next:model-routing:end -->`. Apply the deterministic damaged-marker algorithm — line-based, never parsing the fenced content (the block contains a markdown table):

- Count the `<!-- flow-next:model-routing:start -->` and `<!-- flow-next:model-routing:end -->` lines. If there is **exactly one** start marker **and exactly one** end marker **and** the start line precedes the end line → remove the block inclusive (both markers and everything between them).
- **Any other state** — zero or multiple starts, zero or multiple ends, or end-before-start (out of order) → report the block as damaged and **leave the file untouched**. Never guess which markers pair; a hand-edited file is the user's to fix.

## Report

```
Flow-next uninstall prepared.

Cleaned up:
- Flow-next sections from docs (if existed)
- Model-routing scaffold block from docs (if a well-formed marker pair existed; damaged marker states are reported and left untouched)
- Ralph guard hook entries from project settings (if any fingerprinted entries existed)

Run these commands manually to complete removal:
<commands from above>

Why manual? Destructive commands like rm -rf should have human hands on the keyboard.
If you use DCG (Destructive Command Guard), it will block these commands from AI agents - this is intentional protection.
```
