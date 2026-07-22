---
satisfies: [R4]
---
# fn-123-cursor-first-class-experience-team.2 readonly:true enforcement for read-only agents on Cursor

## Description
Enforce read-only Cursor agents. Add `readonly: true` frontmatter to every canonical agent in `plugins/flow-next/agents/` whose `disallowedTools` already denies Edit AND Write (the read-only scouts/reviewers; roster has 22 agents - derive the set from frontmatter, not a hardcoded list). Cursor ignores `disallowedTools` (its native restriction field is `readonly`), so today these agents run with write access on Cursor. Add `plugins/flow-next/tests/test_cursor_agent_frontmatter.py` (invariant: denies Edit+Write <=> readonly true); strengthen `scripts/sync-codex.sh` guards; regenerate `plugins/flow-next/codex/agents/`.

## Acceptance
- Every canonical agent denying both Edit and Write also declares `readonly: true`; writing agents (worker, plan-sync, pr-comment-resolver, tracker-runner) are NOT marked readonly.
- Claude Code frontmatter stays valid; no changes to existing `model`, `disallowedTools`, or identity fields.
- Codex mirror generation tolerates the extra key; sandbox/model mapping preserved.
- `./scripts/sync-codex.sh` run twice produces identical output; all sync guards green.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
