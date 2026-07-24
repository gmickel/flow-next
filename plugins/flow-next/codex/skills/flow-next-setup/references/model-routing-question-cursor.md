# Model Routing question: Cursor

```json
{
 "header": "Model Routing",
 "question": "Scaffold host-native model routing into AGENTS.md? Enumerates real Cursor model slugs available on this host, then pins a cheap slug for read-only scouts and a cross-family slug for host review (everything else inherits the session model). Date-stamped; re-run setup to refresh volatile ids. Shown in FULL before writing. Background: https://flow-next.dev/orchestration/",
 "options": [
 {"label": "Scaffold", "description": "Write the Cursor host-native model-routing section into AGENTS.md (or the Docs target). Host agent enumerates slugs and picks the pins — never Python."},
 {"label": "Scaffold + enable codex delegation", "description": "Also set work.delegate=codex so /flow-next:work can offload bulk implementation to the codex CLI. First-use consent is still required — this never pre-approves it. INCLUDE THIS OPTION ONLY WHEN HAVE_CODEX=1."},
 {"label": "Skip", "description": "Don't scaffold a routing section (default). Re-run /flow-next:setup later to add it."}
 ],
 "multiSelect": false
}
```

Drop the delegation option object entirely when `HAVE_CODEX=0`.
