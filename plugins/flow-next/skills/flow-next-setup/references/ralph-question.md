# Ralph setup question

This reference is reached only when `RALPH_ASK=1`.

Detect whether the project already has a Ralph surface: `scripts/ralph/` is
present, or a host settings file contains a hook command with
`scripts/ralph/hooks/ralph-guard`. Adjust the spoken introduction to say
"Ralph scaffold is already present — keep it?" when found, but keep the frozen
option labels below. Ralph is fully opt-in; the default install ships zero
hooks and the default answer is No.

Add this object to the grouped Step 6d prompt:

```json
{
  "header": "Ralph",
  "question": "Enable or keep Ralph autonomous mode? Ralph is an opt-in overnight loop that works your backlog while you are away, with guard hooks that limit what it may touch (scaffold lives under scripts/ralph/; hooks register in project settings only if you say yes). Default is off - zero hooks, zero Ralph in normal sessions. Learn more: https://flow-next.dev/ralph/overview/",
  "options": [
    {"label": "No (Recommended)", "description": "Leave Ralph off. Remove any flow-next Ralph guard hook entries from project settings. Note that scripts/ralph/ can be deleted (agent asks before deleting — existing runs/receipts may matter)."},
    {"label": "Yes, enable or keep", "description": "Run /flow-next:ralph-init (scaffold + agent-driven hook merge into project settings). Claude Code's project-hooks trust prompt is the consent gate."}
  ],
  "multiSelect": false
}
```
