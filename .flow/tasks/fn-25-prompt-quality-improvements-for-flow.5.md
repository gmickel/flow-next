# fn-25-prompt-quality-improvements-for-flow.5 Scouts: add Verified/Inferred confidence qualifiers

## Description
Add confidence qualifiers (Verified/Inferred) to scout agent output formats so downstream consumers (planner, worker) know how reliable each finding is.

**Size:** S
**Files:** `plugins/flow-next/agents/repo-scout.md`, `plugins/flow-next/agents/context-scout.md`

## Change details

### repo-scout.md

Update the Output Format section (lines 52-74) to add confidence qualifiers:

In the `### Related Code` section, change from:
```markdown
### Related Code
- `path/to/file.ts:42` - [what it does, why relevant]
```

To:
```markdown
### Related Code
- `path/to/file.ts:42` - [what it does, why relevant] `[VERIFIED]`
- `path/to/inferred.ts` - [likely relevant based on naming] `[INFERRED]`
```

Add a brief note in the Rules section:
```markdown
- **Confidence tags** — append `[VERIFIED]` (confirmed via Read/Grep) or `[INFERRED]` (derived from naming/imports/structure) to findings. VERIFIED = tool output confirmed it. INFERRED = reasonable deduction, not mechanically confirmed.
```

### context-scout.md

Update the Output Format section (lines 209-235) similarly:

In `### Key Files`:
```markdown
### Key Files
- `path/to/file.ts:L10-50` - [what it does] `[VERIFIED]`
- `path/to/other.ts` - [likely related] `[INFERRED]`
```

Add confidence rules to the existing rules section.

### What counts as VERIFIED vs INFERRED

- **VERIFIED**: Agent used Read to see the file content, used Grep and got matches, used structure command and saw the signature, ran a command and got output
- **INFERRED**: Agent saw it in an import chain, filename suggests relevance, directory structure implies it, builder selected it but agent didn't read it

## Investigation targets
**Required** (read before coding):
- `plugins/flow-next/agents/repo-scout.md:52-74` — output format section
- `plugins/flow-next/agents/context-scout.md:209-235` — output format section

## Key context

- Both scouts have `## Output Rules (for planning)` sections at the end — don't duplicate confidence rules there
- Context-scout uses rp-cli `builder` which auto-selects files — those are INFERRED unless agent also ran `read` or `structure` on them
- Keep it lightweight — one tag per finding, not a confidence paragraph
## Acceptance
- [ ] repo-scout output format includes [VERIFIED]/[INFERRED] tags
- [ ] context-scout output format includes [VERIFIED]/[INFERRED] tags
- [ ] Clear definition of VERIFIED vs INFERRED documented in both agents
- [ ] Tags are lightweight (single word in brackets, not verbose)
- [ ] No changes to scout tool access or search behavior
- [ ] Backward compatible — tags are additive to existing output format
## Done summary
Added [VERIFIED]/[INFERRED] confidence qualifiers to repo-scout and context-scout output formats and rules sections. Builder-auto-selected files are INFERRED unless confirmed via read/structure.
## Evidence
- Commits: 98069c75a1eb0c7251913b7475b19e88db3ba896
- Tests: manual review of output format
- PRs: