---
name: flow-next:uninstall
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
```
To complete uninstall, run these commands manually:

rm -rf .flow/bin .flow/usage.md
```

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

## Clean up docs (AI can do this)

For CLAUDE.md and AGENTS.md: if file exists, remove everything between `<!-- BEGIN FLOW-NEXT -->` and `<!-- END FLOW-NEXT -->` (inclusive). This is safe for the AI to execute.

## Report

```
Flow-next uninstall prepared.

Cleaned up:
- Flow-next sections from docs (if existed)

Run these commands manually to complete removal:
<commands from above>

Why manual? Destructive commands like rm -rf should have human hands on the keyboard.
If you use DCG (Destructive Command Guard), it will block these commands from AI agents - this is intentional protection.
```
