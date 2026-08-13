# Model Routing question: Grok

```json
{
  "header": "Model Routing",
  "question": "Scaffold host-native model routing into AGENTS.md? Enumerates Grok's available models at setup (typically grok-4.5 only — single native family), pins a scout slug, and documents that host review fails closed for same-family writers unless a cross-family bridge pin is available. Date-stamped; re-run setup to refresh. Shown in FULL before writing. Background: https://flow-next.dev/orchestration/",
  "options": [
    {"label": "Scaffold", "description": "Write the Grok host-native model-routing section into AGENTS.md (host-review reads this; lifecycle docs may live in CLAUDE.md — Grok loads both). Host agent enumerates models and picks the pins — never Python."},
    {"label": "Scaffold + enable codex delegation", "description": "Also set work.delegate=codex so /flow-next:work can offload bulk implementation to the codex CLI. First-use consent is still required — this never pre-approves it. INCLUDE THIS OPTION ONLY WHEN HAVE_CODEX=1."},
    {"label": "Skip", "description": "Don't scaffold a routing section (default). Re-run /flow-next:setup later to add it."}
  ],
  "multiSelect": false
}
```

Drop the delegation option object entirely when `HAVE_CODEX=0`.
