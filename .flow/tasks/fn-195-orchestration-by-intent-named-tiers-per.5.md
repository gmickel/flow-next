---
satisfies: [R8]
---
# fn-195-orchestration-by-intent-named-tiers-per.5 Docs sweep, dictionary, CHANGELOG, and the full gate

## Description
Close out: the big-picture docs sweep across every page the change touches, the dictionary terms, the major-release CHANGELOG entry, mirror regeneration, and the full gate.

**Size:** M
**Files:** `plugins/flow-next/docs/README.md` (notable updates + index rows), `platforms.md`, `orchestration.md`, `teams.md`, `troubleshooting.md`, `glossary.md`, `plugins/flow-next/README.md`, root `CLAUDE.md` where it describes routing, `CHANGELOG.md`
**Touches:** [plugins/flow-next/docs/**, plugins/flow-next/README.md, CLAUDE.md, CHANGELOG.md]

### Approach
- Sweep by asking which other pages the change touches, not just the obvious ones: the platform pages carried per-host tier tables, teams carried routing advice, troubleshooting carried pin failures, and the notable-updates list needs one line.
- The CHANGELOG entry ships in the same major release as the delegation removal and reads as one story: routing became a preference you write instead of a subsystem you configure. Name the removed keys, the replacement, and the one-line migration. No benchmark tables, no speed claims, no model identifiers beyond the declared exceptions.
- Mirror regenerated twice for idempotency; verify the generator's transforms actually fired on the changed files rather than assuming.
- Full gate: the parallel suite with the exit code captured directly, plus the pinned linter. Docs trees here are test-pinned and the local classifier calls them docs-only, so the full suite runs regardless of tier.

### Investigation targets
**Required** (read before writing):
- `agent_docs/releasing.md` - the changelog register and what a major requires
- `plugins/flow-next/docs/README.md` notable-updates format

### Acceptance
- [ ] Every page the change touches is updated, not only the routing page; notable-updates line added
- [ ] Four tier terms in the dictionary with synonym bans
- [ ] `## Unreleased` CHANGELOG entry framed for the major release, one story with the delegation removal, migration line included; no version bump
- [ ] Mirror regenerated twice with transforms verified on the changed files
- [ ] Full suite + linter green with exit codes captured directly; OS matrix green in CI

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
