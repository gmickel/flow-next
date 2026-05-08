---
satisfies: [R14]
---

## Description

Update the slash-command prompt files under `plugins/flow-next/commands/flow-next/` for spec vocabulary. Each is short prose (3-line) but user-visible -- the slash-command file body is the prompt the host agent reads when the user types `/flow-next:<name>`.

**Size:** S
**Files:**
- `plugins/flow-next/commands/flow-next/capture.md` (3 refs)
- `plugins/flow-next/commands/flow-next/interview.md` (2 refs)
- `plugins/flow-next/commands/flow-next/make-pr.md` (2 refs)
- `plugins/flow-next/commands/flow-next/uninstall.md` (1 ref)

## Approach

- Per-file: replace "epic" prose -> "spec"; replace `flowctl epic *` -> `flowctl spec *`; replace `<epic-id>` argument hints -> `<spec-id>`.
- These files are 5-15 lines each -- minimal scope.
- Note: `commands/flow-next/epic-review.md` is handled in T6 (the dedicated rename task); not touched here.
- Note: the `commands/flow-next/spec-completion-review.md` file is also created in T6, not here.

## Investigation targets

**Required:** all 4 files listed above.

## Acceptance

- [ ] `capture.md`, `interview.md`, `make-pr.md`, `uninstall.md` use spec vocabulary; no `flowctl epic` references; no `<epic-id>` argument hints.
- [ ] Frontmatter `description:` field updated where it mentions epic.

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
