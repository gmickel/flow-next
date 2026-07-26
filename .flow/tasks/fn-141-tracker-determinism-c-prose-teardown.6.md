---
satisfies: [R16, R17]
---
# fn-141-tracker-determinism-c-prose-teardown.6 flow-next.dev docs site + CHANGELOG (same workstream)

## Description
Update `~/work/flow-next.dev` in the same workstream per the repo's standing downstream rule. This is a user-facing command and behavior change, so in-repo docs alone are insufficient.

Pages: `teams/tracker-sync.mdx` (the transport-ladder narrative is the most user-facing statement that becomes wrong), `teams/collaboration.mdx`, `flowctl/commands.mdx`, `flowctl/cli-reference.mdx`, `flowctl/configuration.mdx` (new `tracker.resolved` block), `reference/glossary.mdx`, `skills/pilot.mdx`, `skills/sync.mdx`, `autonomous/land.mdx`.

Stage a CHANGELOG entry under `## Unreleased`. **No version bump** - the batch bumps once at release.

## Acceptance
- [ ] No docs-site page teaches runtime transport-ladder reasoning
- [ ] `flowctl/configuration.mdx` documents `tracker.resolved` incl. capabilities
- [ ] New verbs documented with envelope + class enum
- [ ] `pnpm build` green
- [ ] Committed separately in the flow-next.dev repo
- [ ] CHANGELOG staged under Unreleased; NO version bump

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
