---
satisfies: [R37]
---
# fn-139-tracker-sync-determinism-flowctl-owns.11 flow-next.dev docs-site update (same workstream)

## Description
Update `~/work/flow-next.dev` in the same workstream, per the repo's standing downstream rule. This is a user-facing command and behavior change, so in-repo docs alone are insufficient.

Pages identified by the docs-gap scout: `teams/tracker-sync.mdx` (the transport-ladder narrative is the most user-facing statement that becomes wrong), `teams/collaboration.mdx`, `flowctl/commands.mdx`, `flowctl/cli-reference.mdx`, `flowctl/configuration.mdx` (new `tracker.resolved` block), `reference/glossary.mdx`, `skills/pilot.mdx`, `skills/sync.mdx`, `autonomous/land.mdx`, plus a `releases/changelog.mdx` entry at release time.

Commit separately in the flow-next.dev repo.

## Acceptance
- [ ] No docs-site page still teaches runtime transport-ladder reasoning
- [ ] `flowctl/configuration.mdx` documents `tracker.resolved` incl. capabilities
- [ ] New `flowctl tracker` verbs documented with the result envelope and class enum
- [ ] `pnpm build` green (75+ pages)
- [ ] Committed separately in the flow-next.dev repo

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
