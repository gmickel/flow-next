# capture — optional codebase verification (R12) (loaded on demand)

> Loaded ONLY when the conversation references repo files or modules whose state matters for the
> spec. A clean conversation with no file references — or with only 1-2, investigated on the main
> thread — never reads this file.

## 1.2 — Optional codebase verification (subagent dispatch — R12)

When the conversation references repo files or modules whose state matters for the spec ("the auth module needs X", "we already have a rate limiter at..."), spawn a **read-only investigation subagent** via the `Task` tool with `subagent_type: Explore` (or `general-purpose` when Explore is unavailable; on hosts with neither builtin — e.g. Cursor — the host's generic subagent dispatch with Edit/Write disallowed). For clean conversations with no file references, skip this step. ( per repo cross-platform convention.)

Investigation subagents are **read-only**. They must not Edit, Write, Bash beyond Read / Grep / Glob, or git-mutate. Pass `disallowedTools: Edit, Write, Task` when dispatching. Each returns:

```yaml
references_verified:
 - path: src/auth/oauth.ts
 exists: true
 last_modified: "2026-03-12"
references_missing:
 - path: src/legacy/auth_v1.ts
 note: "user mentioned but file not found; possibly already removed"
related_modules_found:
 - path: src/auth/middleware.ts
 relevance: "implements existing OAuth flow user wants to extend"
```

When spawning subagents, include this directive in the task prompt:

> Use Read, Grep, Glob for all file investigation. Do NOT use shell commands (`ls`, `find`, `cat`, `grep`, `bash`) for file operations. This avoids permission prompts and is more reliable. Do NOT edit, create, or delete any files. Return only the structured payload defined in the workflow.

The orchestrator (this skill, on the main thread) merges results into Phase 2's `[inferred]` confidence — verified references can be tagged `[paraphrase]`; unverified or missing files stay `[inferred]` and surface in Phase 4 read-back for explicit user confirmation.

For 1-2 file references, investigate on the main thread — no subagent overhead is worth it.
