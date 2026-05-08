---
satisfies: [R15, R17]
---

## Description

Update top-level user-facing documentation surfaces with spec vocabulary. The setup-template files (`flow-next-setup/templates/{usage,agents-md-snippet,claude-md-snippet}.md`) are owned by T9 (=fn-43...10) -- this task focuses on the user-visible surfaces outside the skill directories AND the working-copy `.flow/usage.md` in this repo (R17 working-copy half).

**Size:** M
**Files:**
- `README.md` (root, 4 refs)
- `plugins/flow-next/README.md` (133 refs)
- `CLAUDE.md` (root, 24 refs in the Flow-Next subsection)
- `.flow/usage.md` (15 refs -- the working-copy in THIS repo; setup templates that regenerate it for users live in T9)

## Approach

- Wholesale "epic" -> "spec" prose pass across the 4 files.
- CLI verb examples updated throughout: `flowctl epic create` -> `flowctl spec create`, etc.
- Filesystem path examples: `.flow/epics/` -> `.flow/specs/` for JSON sidecars.
- Plugin README: add a "Deprecation timeline" subsection near install instructions.
- Plugin README command count stays at 18 (epic-review renamed to spec-completion-review, redirect command file at `epic-review.md` keeps the count).
- Plugin README command table row for `/flow-next:epic-review` -> `/flow-next:spec-completion-review`.
- Root CLAUDE.md "Flow-Next" subsection: rewrite command lists, "Creating a spec" section heredocs.
- `.flow/usage.md`: direct edit for the working copy in this repo (R17 working-copy half).

## Investigation targets

**Required:**
- `plugins/flow-next/README.md` (133 refs).
- `CLAUDE.md` (root, Flow-Next subsection).
- `README.md` (root).
- `.flow/usage.md`.

## Key context

- `plugins/flow-next/README.md` is the most-referenced single doc surface.
- AGENTS.md is a symlink to CLAUDE.md. Edit the file CLAUDE.md points at.
- Setup template files live in T9's scope.

## Acceptance

- [ ] All 4 files updated; zero `flowctl epic` references in user-facing prose (deprecation context exempted).
- [ ] Plugin README has a "Deprecation timeline" subsection.
- [ ] Plugin README command table has `/flow-next:spec-completion-review` row.
- [ ] Root CLAUDE.md "Flow-Next" subsection uses spec vocabulary; heredocs use `flowctl spec create + spec set-plan`.
- [ ] `.flow/usage.md` (the working-copy in this repo) uses spec vocabulary (R17).

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
