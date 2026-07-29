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
Added the primary Unreleased entry for tracker determinism specs A, B, and C without a version bump. Updated the flow-next.dev tracker documentation across all named pages and sibling stale runtime references, documented the deterministic flowctl tracker contract, and committed the green site build separately as 664b5cb8a34545202cec1bfa098fee528f2e6ea9.
## Evidence
- Commits: 5bf4db26b033c346d5864af5031b88f3c10645c3
- Tests: GATE_SKIPPED:unittest:docs-only - cumulative diff classified tier-B (no executable paths touched), cd /Users/gordon/work/flow-next.dev && pnpm build, rg -n -i 'transport ladder|transport-ladder|tracker-runner|transport-blind|MCP rung|flowctl gains no tracker-mutation|rest/api/3|ADF' src/content/docs (zero stale positive runtime guidance; one accurate negative ADF statement), Codex impl-review SHIP: /tmp/impl-review-receipt-fn-141-tracker-determinism-c-prose-teardown.6.json, flow-next.dev commit 664b5cb8a34545202cec1bfa098fee528f2e6ea9
- PRs: