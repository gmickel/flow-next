# Docs question (gated reference)

> Read from workflow.md Step 6d only when the Docs question is included (unanswered, and docs are
> not current). Use the block for this run's `PLATFORM`.

**Docs question** (include only when unanswered and docs are not current — adjust default based on platform):

For **Codex** (`PLATFORM=codex`):
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions? Adds a marker-bounded section teaching any agent that opens this repo how to track work via flowctl; your text outside the markers is never touched.",
  "options": [
    {"label": "AGENTS.md only (Recommended)", "description": "Add flow-next section to AGENTS.md (Codex reads this)"},
    {"label": "CLAUDE.md only", "description": "Add flow-next section to CLAUDE.md"},
    {"label": "Both", "description": "Add flow-next section to both files"},
    {"label": "Skip", "description": "Don't update documentation"}
  ],
  "multiSelect": false
}
```

For **Claude Code / Droid**:
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions? Adds a marker-bounded section teaching any agent that opens this repo how to track work via flowctl; your text outside the markers is never touched.",
  "options": [
    {"label": "CLAUDE.md only", "description": "Add flow-next section to CLAUDE.md"},
    {"label": "AGENTS.md only", "description": "Add flow-next section to AGENTS.md"},
    {"label": "Both", "description": "Add flow-next section to both files"},
    {"label": "Skip", "description": "Don't update documentation"}
  ],
  "multiSelect": false
}
```

For **Cursor** (`PLATFORM=cursor`) and **Muse** (`PLATFORM=muse`) — both read AGENTS.md (Muse uses it ahead of CLAUDE.md), so recommend it (the `/flow-next:` snippet is wired in Step 7's write mapping, NOT the Codex `$flow-next-` one):
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions? Adds a marker-bounded section teaching any agent that opens this repo how to track work via flowctl; your text outside the markers is never touched.",
  "options": [
    {"label": "AGENTS.md only (Recommended)", "description": "Add flow-next section to AGENTS.md (Cursor and Muse read this)"},
    {"label": "CLAUDE.md only", "description": "Add flow-next section to CLAUDE.md"},
    {"label": "Both", "description": "Add flow-next section to both files"},
    {"label": "Skip", "description": "Don't update documentation"}
  ],
  "multiSelect": false
}
```

For **Grok** (`PLATFORM=grok`) — Grok reads BOTH CLAUDE.md and AGENTS.md; lifecycle snippet defaults to CLAUDE.md (canonical Claude-format target, named by Claude-format skill id — NOT the Codex `$flow-next-` form). A pre-existing wrong Codex `$flow-next-` marker block is consent-refreshed to the slash form (marker-scoped; text outside markers untouched). The routing block still targets AGENTS.md (where host-review workflows read it):
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions? Adds a marker-bounded section teaching any agent that opens this repo how to track work via flowctl; your text outside the markers is never touched. Grok loads both CLAUDE.md and AGENTS.md.",
  "options": [
    {"label": "CLAUDE.md only (Recommended)", "description": "Add flow-next section to CLAUDE.md (canonical Grok lifecycle target; Claude-format skill ids)"},
    {"label": "AGENTS.md only", "description": "Add flow-next section to AGENTS.md"},
    {"label": "Both", "description": "Add flow-next section to both files (recommended when you also want the routing block's sibling lifecycle snippet nearby)"},
    {"label": "Skip", "description": "Don't update documentation"}
  ],
  "multiSelect": false
}
```

For **OpenCode** (`PLATFORM=opencode`) — OpenCode reads AGENTS.md. Command stubs are the flat `/flow-next-<name>` form (not `/flow-next:<name>`, not `$flow-next-`). The Claude-flavor snippet is rewritten `/flow-next:` → `/flow-next-` before apply (6b temp-template block); the routing block also targets AGENTS.md:
```json
{
  "header": "Docs",
  "question": "Update project documentation with Flow-Next instructions? Adds a marker-bounded section teaching any agent that opens this repo how to track work via flowctl; your text outside the markers is never touched.",
  "options": [
    {"label": "AGENTS.md only (Recommended)", "description": "Add flow-next section to AGENTS.md (OpenCode reads this; slash form is /flow-next-<name>)"},
    {"label": "CLAUDE.md only", "description": "Add flow-next section to CLAUDE.md"},
    {"label": "Both", "description": "Add flow-next section to both files"},
    {"label": "Skip", "description": "Don't update documentation"}
  ],
  "multiSelect": false
}
```
