# Model Routing question: Claude Code, Droid, Codex

Add this question only when the workflow gate selected this reference:

```json
{
 "header": "Model Routing",
 "question": "Scaffold a recommended multi-model pipeline into your project instruction file? This writes a starting-point section - a cost/speed/intelligence/taste scores table plus rules for which model plans, implements, and reviews - wired to the bridge CLIs detected on this machine. Shown in FULL before writing; yours to edit after. Background: https://flow-next.dev/orchestration/",
 "options": [
 {"label": "Scaffold", "description": "Write the model-routing example into the same CLAUDE.md/AGENTS.md the Docs step targets. Shown in full before writing; these are starting opinions you edit down, not up."},
 {"label": "Scaffold + enable codex delegation", "description": "Also set work.delegate=codex so /flow-next:work can offload bulk implementation to the codex CLI. First-use consent is still required — this never pre-approves it. INCLUDE THIS OPTION ONLY WHEN HAVE_CODEX=1."},
 {"label": "Skip", "description": "Don't scaffold a routing section (default). Re-run /flow-next:setup later to add it."}
 ],
 "multiSelect": false
}
```

Drop the delegation option object entirely when `HAVE_CODEX=0`.
