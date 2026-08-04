---
satisfies: [R9]
---
# fn-167-bugbot-pre-push-review-stage.3 Docs: repo, then the full downstream property chain

## Description
No ship without docs, and repo docs are not the end of the chain. Read `~/work/agent-instructions/downstream-properties.md` and walk the whole thing.

### Repo

- Pipeline description wherever the stage sequence is documented (CLAUDE.md, `docs/ralph.md`, `usage.md`).
- `docs/flowctl.md`: `pipeline.prepushReview` config row alongside the existing `pipeline.qa` row.
- The new skill's own SKILL.md front matter and description.
- CHANGELOG entry.

### What the docs must say, not just that the flag exists

- **Cursor host only**, and why: `/review-bugbot` is reachable when flow-next is the Cursor agent, not through headless `cursor-agent -p`, until Cursor ships CLI support for the skill.
- **It costs usage.** Every run consumes Cursor usage, and on Individual plans it draws from the pool shared with coding. This is why the stage is off by default. State it plainly rather than burying it.
- **What it replaces**: the post-PR remote Bugbot review, relocated to pre-push. Not an extra round. Make clear the dedup is Bugbot-specific and that no other reviewer has an equivalent, so nobody expects the same economics elsewhere.
- **Recommended pairing**: Bugbot pre-push plus a different-family reviewer on the PR (Codex), which is also what the cross-model review evidence argues for.
- **The general rule worth stating once**: the land loop is only economical under a reviewer with either a separate quota or flat per-seat pricing. A per-review-priced reviewer sharing a pool with the coding agent is actively anti-correlated with an agent-driven loop.
- The churn non-goal, so a future contributor does not add the fix loop by reflex.

### Downstream chain

- flow-next.dev
- microsite + AI x SDLC guide
- vault

Each property gets the update it needs, not a copy-paste of the repo docs.

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
