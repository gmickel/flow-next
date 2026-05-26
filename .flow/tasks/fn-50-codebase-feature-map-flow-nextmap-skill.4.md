---
satisfies: [R6]
---

## Description

Add a one-paragraph optional-add mentioning `/flow-next:map` to root `CLAUDE.md` AND both setup-template snippets (`claude-md-snippet.md`, `agents-md-snippet.md`). The two setup templates must be byte-identical to the canonical snippet text (modulo `/flow-next:map` vs `$flow-next-map` syntax convention) so fn-45.3's byte-compare gate propagates on next `/flow-next:setup` in user repos.

**Size:** S
**Files:**
- `CLAUDE.md` (root) — add row to "Where to look" table + the optional-add paragraph
- `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md` — one-paragraph optional-add inside `<!-- BEGIN FLOW-NEXT -->` block
- `plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md` — same paragraph with Codex syntax

**Depends on** fn-50.1 (skill must exist before docs reference it — avoids dead-reference window per decision lock-in #5).

## Approach

**Root `CLAUDE.md`** at line 89 has the "Where to look" table. Add ONE row pointing at the skill (e.g., `Codebase feature map (optional)` → backtick path to `plugins/flow-next/skills/flow-next-map/` or just mention `/flow-next:map` skill). Add a brief one-paragraph optional-add (max 3 sentences) before or after the table — explain what the skill does and that it's opt-in.

**Setup templates** at `plugins/flow-next/skills/flow-next-setup/templates/{claude-md-snippet,agents-md-snippet}.md` (both 40 lines, wrapped in `<!-- BEGIN FLOW-NEXT -->` markers). Both files MUST be edited in tandem with byte-identical prose (modulo command syntax: `/flow-next:map` for Claude convention; `$flow-next-map` for Codex/AGENTS convention per the existing snippet pattern).

**Critical byte discipline:** fn-45.3's byte-compare gate at `plugins/flow-next/skills/flow-next-setup/workflow.md:532-546` is byte-for-byte INCLUDING whitespace. Any trailing-space drift between the snippet file and what's installed in user repos blocks auto-propagation. Author with:
- LF (not CRLF) line endings
- No trailing whitespace on lines
- Final newline at EOF
- Identical whitespace before/after the new paragraph in both snippet files (modulo only the command syntax token)

**One-paragraph wording** (concrete proposal — implementer can tighten):

> Optional: `/flow-next:map` wraps [openclaw/clawpatch](https://github.com/openclaw/clawpatch)'s `clawpatch map` command to build a semantic feature index under `.clawpatch/features/*.json`. When present, `repo-scout` and `context-scout` use it to anchor R-IDs and `Investigation targets` to concrete codebase regions. Provider-free by default; install via `pnpm add -g clawpatch` (Node 22+).

For the AGENTS.md mirror, replace `/flow-next:map` with `$flow-next-map`.

**Sanity test** before commit: byte-diff the two snippet files to confirm only the command-syntax token differs.

## Investigation targets

**Required** (read before coding):
- `CLAUDE.md` (root, lines 89-107) — "Where to look" table style
- `plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md` — full file (40 lines)
- `plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md` — full file (40 lines)
- `plugins/flow-next/skills/flow-next-setup/workflow.md:532-546` — byte-compare gate impl (the propagation mechanism)

**Optional**:
- `CLAUDE.md` line 117 — root `<!-- BEGIN FLOW-NEXT -->` block (this repo's own copy; will get the new content on next `/flow-next:setup` here)

## Key context

- The byte-compare gate is in skill prose, NOT flowctl Python. It runs during `/flow-next:setup` re-run.
- Three outcomes: (a) no marker block → append; (b) marker block + identical bytes → no-op; (c) marker block + customized → `AskUserQuestion` Keep/Overwrite/abort.
- Users with customized snippets get prompted; users with stable snippets auto-receive the new paragraph.
- This task is the smallest-LOC change in fn-50 but the most byte-sensitive.

## Acceptance

- [ ] R6: Root `CLAUDE.md` gains one row in "Where to look" table referencing `/flow-next:map` + a one-paragraph optional-add (under 3 sentences)
- [ ] R6: `claude-md-snippet.md` gains the same paragraph inside the `<!-- BEGIN FLOW-NEXT -->` block, syntax `/flow-next:map`
- [ ] R6: `agents-md-snippet.md` gains the same paragraph, syntax `$flow-next-map`
- [ ] R6: Byte-diff between the two snippet files shows ONLY the command-syntax token difference (no whitespace drift, no extra newlines)
- [ ] R6: Both snippet files end with a single trailing newline; no trailing whitespace on any line
- [ ] Manual smoke: re-run `/flow-next:setup` against this dev repo — the new paragraph either appends (if absent) or no-ops (if already in sync); no AskUserQuestion fires unless this repo's CLAUDE.md is customized

## Done summary
Added one-paragraph optional-add for `/flow-next:map` to root CLAUDE.md (new "Where to look" row + paragraph below the table) and to both `flow-next-setup/templates/claude-md-snippet.md` and `agents-md-snippet.md` inside the `<!-- BEGIN FLOW-NEXT -->` block. Byte-discipline preserved: diff between the two snippet files shows exactly 3 hunks, all command-syntax-token only (`/flow-next:map` vs `$flow-next-map`, plus the two pre-existing `plan`/`interview`/`setup` token hunks); no whitespace drift, LF line endings, single trailing newline at EOF — fn-45.3 byte-compare gate will propagate cleanly on next `/flow-next:setup` in user repos.
## Evidence
- Commits: 4bc3a8a9dfacc2feefc4da40026dbb0fbe4b6f45
- Tests: diff plugins/flow-next/skills/flow-next-setup/templates/claude-md-snippet.md plugins/flow-next/skills/flow-next-setup/templates/agents-md-snippet.md (only command-syntax-token hunks present), grep -n ' $' on both snippet files (no trailing whitespace), tail -c 20 | xxd (final LF newline at EOF), wc -l (42 lines, both files), flowctl triage-skip --base c39a893... --json (verdict=SHIP, mode=triage_skip, reason=docs-only)
- PRs: