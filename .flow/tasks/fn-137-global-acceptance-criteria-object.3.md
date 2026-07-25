---
satisfies: [R3]
---
# fn-137-global-acceptance-criteria-object.3 Setup scaffold opt-in

## Description
Setup offers the criteria scaffold; declining leaves no trace.

**Size:** S

**Files:** setup skill prose (both canonical + sync-codex), a template criteria file (bundled), tests where setup artifacts are tested.

### Approach
- Setup gains an opt-in question (existing setup question conventions; AskUserQuestion canonical + numbered-prompt mirror) offering .flow/criteria.md scaffold; template documents the G-ID grammar with 2-3 commented examples.
- Respect setup-modes (copy vs plugin) per agent_docs/setup-modes.md resolution chains.

## Acceptance
- [ ] Opt-in scaffold w/ documented template; decline = no trace; both setup modes honored; sync-codex idempotent (R3).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
