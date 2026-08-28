---
satisfies: [R1]
---
# fn-209-no-plan-work-route-tool-permission-audit.1 Tool-permission audit: remove writer Task denials, rationale on read-only, doc + parity pass

## Description
Land the R1 audit pass across agent frontmatter, the docs that describe it, the strategy-skill allowlist verdict, and the Cursor/Grok parity check. Split this way because it is the only task touching agents/** and the permission docs.

**Size:** M
**Files:** `plugins/flow-next/agents/worker.md`, `plugins/flow-next/agents/pr-comment-resolver.md`, `plugins/flow-next/agents/plan-sync.md`, all read-only `plugins/flow-next/agents/*.md`, `CLAUDE.md`, `plugins/flow-next/docs/platforms.md`, `plugins/flow-next/skills/flow-next-strategy/SKILL.md`
**Touches:** [plugins/flow-next/agents/**, CLAUDE.md, plugins/flow-next/docs/platforms.md, plugins/flow-next/skills/flow-next-strategy/SKILL.md]

### Approach
- `worker.md:5` and `pr-comment-resolver.md:5`: remove the whole `disallowedTools: Task` line (Task is the only token). `plan-sync.md:4`: `Task, Write, Bash` -> `Write, Bash`.
- Every read-only agent keeps `disallowedTools: Edit, Write, Task` and gains a one-line inline rationale comment (NEW convention - no existing example; keep it to one short line, e.g. `# read-only: Task would be a write escape hatch via a spawned writing subagent`). Verify the comment survives sync-codex (frontmatter comments are swallowed by the mirror's case parser - confirm, do not assume) and the OpenCode generator's closed key parsing.
- `CLAUDE.md` (Agent permissions bullet + checklist item) and `platforms.md` deny-list prose: distinguish read-only agents (deny all three, with the escape-hatch rationale) from writing agents (deny Edit/Write subsets only), and add one line: Task is subagent dispatch (renamed Agent in Claude Code v2.1.63), not a planning tool.
- Strategy skill verdict: `flow-next-strategy/SKILL.md:5` lacks Edit while pilot/land/map carry it. Read its maintain path; either add Edit or record Write-only as deliberate in a one-line comment beside the allowlist.
- Cursor/Grok parity check (short, evidence-based): confirm Cursor honors `disallowedTools`/`readonly` on canonical files and Grok's Claude-plugin compat leaves the post-audit model intact; record findings (dated) in `platforms.md` only if behavior differs.
- Do NOT touch `phases.md` or `references/host-deferred-review.md` here - the host-deferred rationale fix belongs to task 2 (file ownership).
- Note for reviewers: the mandated frontmatter rationale comment is NOT a "comment as alibi" under worker.md's new :214-222 rule - it documents an invariant on a config key, not a workaround; say so in the commit message if flagged.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/agents/plan-sync.md:1-8` - frontmatter shape to edit
- `scripts/sync-codex.sh:1857-1888` - frontmatter case parser (`disallowedTools:*)` at :1882 swallows the whole line incl. trailing comments; `""|\#*)` at :1885 swallows whole-line comments; no default arm - unknown keys drop silently)
- `plugins/flow-next/scripts/lib/opencode_generate.py:47-100` - token map + closed allowlist the comment must not break
- `plugins/flow-next/tests/test_cursor_agent_frontmatter.py:78-135` - Edit+Write invariants that must stay green

**Optional:**
- `plugins/flow-next/tests/test_opencode_agent_frontmatter.py` - dynamic reads, run to confirm

### Acceptance
- [ ] worker + pr-comment-resolver carry no Task denial; plan-sync denies exactly Write, Bash
- [ ] every read-only agent still denies Edit, Write, Task and carries the one-line rationale
- [ ] CLAUDE.md + platforms.md describe the post-audit model incl. the v2.1.63 rename fact
- [ ] strategy allowlist has a recorded verdict (Edit added, or deliberate Write-only noted)
- [ ] Cursor/Grok parity check done with dated evidence; platforms.md updated only on a real difference
- [ ] `python3 -m unittest test_cursor_agent_frontmatter test_opencode_agent_frontmatter -q` green

### Acceptance
- [ ] TBD

### Done summary
TBD

### Evidence
- Commits:
- Tests:
- PRs:
## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
