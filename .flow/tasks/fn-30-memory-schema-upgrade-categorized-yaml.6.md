# fn-30-memory-schema-upgrade.6 flowctl memory discoverability-patch

## Description

New optional command that patches the project's root AGENTS.md or CLAUDE.md with a one-line reference to `.flow/memory/` so agents without flow-next skills loaded can still discover the learnings store.

**Size:** S

**Files:**
- `plugins/flow-next/scripts/flowctl.py` — `cmd_memory_discoverability_patch`
- `.flow/bin/flowctl.py` (mirror)

## CLI signature

```
flowctl memory discoverability-patch [--apply] [--target agents|claude|auto] [--dry-run] [--json]
```

- `--apply`: write the change (default: prompt for confirmation)
- `--target auto` (default): pick based on which file is "substantive" (non-shim)
- `--target agents`: force AGENTS.md
- `--target claude`: force CLAUDE.md
- `--dry-run`: print planned edit without writing

## Behavior

1. **Find instruction files** at project root: `AGENTS.md`, `CLAUDE.md`.
   - If neither exists, print "No AGENTS.md or CLAUDE.md at repo root. Create one first, then re-run." and exit 1.

2. **Determine substantive file**. Sometimes one is a shim:
   - `CLAUDE.md` containing only `@AGENTS.md` → shim; substantive file is AGENTS.md
   - `AGENTS.md → CLAUDE.md` symlink → substantive file is CLAUDE.md
   - Both non-shim → prefer AGENTS.md (industry default)

3. **Scan substantive file** for any existing mention of `.flow/memory/`, `flowctl memory`, or similar. Substring match is fine.
   - If found → print "Discoverability already present. No changes needed." and exit 0.

4. **Identify best insertion point**. Scan for headings:
   - Directory layout / File structure section → insert line in a bulleted list
   - Tooling / Commands section → insert a command reference
   - Otherwise → append a short new section at end

5. **Draft the edit**:

   ```markdown
   ## Memory / Learnings

   `.flow/memory/` — categorized learnings store (bug + knowledge tracks). Relevant when implementing or debugging in documented areas.

   Commands:
   - `flowctl memory search <query>` — find entries
   - `flowctl memory list --category <cat>` — list by category
   ```

   Or, for directory listings, a single line:

   ```
   .flow/memory/       # categorized learnings (flowctl memory search)
   ```

6. **Present diff + prompt** for confirmation (unless `--apply`):

   ```
   Proposed change to AGENTS.md:

   + ## Memory / Learnings
   + 
   + `.flow/memory/` — categorized learnings store (bug + knowledge tracks)...

   Apply? [y/N]
   ```

7. **Write** on confirmation.

## JSON output

```json
{
  "success": true,
  "target": "AGENTS.md",
  "action": "applied|skipped|exists",
  "diff": "..."
}
```

## Rationale

Agents running on a project without the flow-next plugin loaded (e.g., a generic Claude Code session, a Codex helper) won't know `.flow/memory/` exists unless the project's canonical instruction file surfaces it. MergeFoundry upstream's discoverability-check pattern is the same idea — get the knowledge store into the file every agent reads.

## Ralph compatibility

User-triggered. Ralph does not invoke this. Zero impact on autonomous loops.

## Acceptance

- **AC1:** Command exists and is callable as `flowctl memory discoverability-patch`.
- **AC2:** Identifies AGENTS.md vs CLAUDE.md substantive file correctly (handles shims, symlinks).
- **AC3:** Skips gracefully with "already present" when `.flow/memory/` is referenced.
- **AC4:** Draft edit is contextually placed (in existing directory listing if present, else new section).
- **AC5:** `--dry-run` prints diff without writing.
- **AC6:** Without `--apply`, prompts for confirmation; declining aborts.
- **AC7:** `--apply` writes atomically.
- **AC8:** `--json` output matches schema.

## Dependencies

- fn-30-memory-schema-upgrade.1 (tree must exist to make discoverability meaningful — though the command works even on empty trees)

## Out of scope

- Auto-running on `memory init` (keep it manual).
- Patching sub-directory instruction files (only root).
- Supporting arbitrary project docs (only AGENTS.md / CLAUDE.md).

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
