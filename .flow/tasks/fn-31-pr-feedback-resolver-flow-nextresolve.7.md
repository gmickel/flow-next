# fn-31-pr-feedback-resolver.7 Docs, website, codex mirror, version bump

## Description

Rollup: CHANGELOG, READMEs, CLAUDE.md, website page, codex regeneration, version bump.

**Size:** M (docs only)

**Files:**
- `CHANGELOG.md`
- `README.md` (root)
- `plugins/flow-next/README.md`
- `CLAUDE.md`
- `/Users/gordon/work/mickel.tech/app/apps/flow-next/page.tsx`
- `plugins/flow-next/.claude-plugin/plugin.json` (via bump.sh)
- `plugins/flow-next/.codex-plugin/plugin.json` (via bump.sh)
- `.claude-plugin/marketplace.json` (via bump.sh)
- `plugins/flow-next/codex/**` (via sync-codex.sh — auto-regenerated)

## Change details

### CHANGELOG.md

```markdown
## [flow-next 0.35.0] - YYYY-MM-DD

### Added
- **`/flow-next:resolve-pr` — PR feedback resolver.** New user-triggered command for resolving GitHub PR review threads. Fetches unresolved threads, triages new vs pending-decision, dispatches parallel (Claude Code) or serial (Codex/Copilot/Droid) resolver agents, validates combined state, commits + pushes fixes, replies and resolves via GraphQL.
- **Handles all three feedback surfaces:** inline review threads, top-level PR comments, review submission bodies. GraphQL resolves threads; PR-comment replies via `gh pr comment`.
- **Cross-invocation cluster analysis.** When multiple review rounds reveal recurring patterns in the same file/subtree, dispatches a cluster-aware resolver that investigates broader area before making targeted fixes. Gated on both: prior-resolved threads exist AND spatial-overlap with new threads.
- **Targeted mode:** pass a comment URL to resolve a single thread only.
- **`--dry-run` flag:** fetch + plan, no edits/commits/replies.
- **`--no-cluster` flag:** skip cluster analysis, all items individual.
- **`pr-comment-resolver` agent:** single-thread resolver subagent with read-only investigation (git/gh) + Edit/Write for fixes, never commits/pushes (orchestrator owns that).
- **GraphQL scripts bundled:** `get-pr-comments`, `get-thread-for-comment`, `reply-to-pr-thread`, `resolve-pr-thread`. Zero runtime deps beyond `gh` + `jq`.

### Notes
- User-triggered only. Ralph autonomous loop is unaffected — no automatic invocation, no receipt writes, no shared state.
- Safety: comment text is untrusted input; resolvers never execute shell commands from comment bodies.
- Verify loop bounded at 2 fix-verify cycles; 3rd attempt escalates pattern to user.
- Smoke test: `plugins/flow-next/scripts/resolve-pr_smoke_test.sh`.
```

### README.md (root)

Add one sentence to the flow-next feature list mentioning `/flow-next:resolve-pr`.

### plugins/flow-next/README.md

New section "PR Feedback Resolution":

- Command signature + invocation modes (full, PR number, comment URL)
- Flag reference (`--dry-run`, `--no-cluster`)
- Brief description of phases
- Safety notes (untrusted input, bounded cycles)
- Link to CHANGELOG for details

Also update the commands list at the top.

### CLAUDE.md (root)

Add bullet under flow-next section:

```markdown
- `/flow-next:resolve-pr [PR# | comment URL]` — resolve PR review threads (fetch → triage → dispatch → validate → commit → reply → resolve). User-triggered; Ralph does not invoke. Flags: `--dry-run`, `--no-cluster`.
```

### Website: `~/work/mickel.tech/app/apps/flow-next/page.tsx`

Update:
- Version string → 0.35.0 (or whatever chains after Epic 2)
- Metadata description — add "PR feedback resolution" keyword
- Feature grid — add a new card/item for the resolver
- FAQ — potentially add an entry ("How do I handle PR review comments with flow-next?")

### sync-codex + bump

```bash
scripts/sync-codex.sh
scripts/bump.sh minor flow-next   # minor bump: new user-facing command
```

### Tag + release

```bash
git tag flow-next-v0.35.0
git push origin flow-next-v0.35.0
```

## Acceptance

- **AC1:** CHANGELOG has `[flow-next 0.35.0]` entry describing the resolver + flags + safety rules.
- **AC2:** Root README.md mentions resolve-pr in feature list.
- **AC3:** plugin README.md has dedicated "PR Feedback Resolution" section.
- **AC4:** CLAUDE.md root has bullet mentioning the command + flags + Ralph-out nature.
- **AC5:** Website page updated: version + feature mention.
- **AC6:** sync-codex.sh includes the new skill + agent + scripts in `plugins/flow-next/codex/`.
- **AC7:** bump.sh updates all three manifests + README badge.
- **AC8:** Tag pushed (or staged) to trigger release.

## Dependencies

- All fn-31 sibling tasks (1-6) merged first.

## Out of scope

- Cross-promotion with Epic 1 / Epic 2 (separate releases).
- Discord announcement (default release automation).

## Done summary
Version-bumped flow-next to 0.34.0 (minor) and rolled up PR resolver docs across CHANGELOG, root + plugin README, CLAUDE.md, website page (~/work/mickel.tech), and codex mirror. scripts/sync-codex.sh regenerated 17 skills + 21 agents, including flow-next-resolve-pr skill and pr-comment-resolver agent. All smoke tests green: flowctl smoke (99 passing) + resolve-pr smoke (58 passing).
## Evidence
- Commits: 6d546869a3041eb5e83d12ee45e49339a3fb04d0
- Tests: plugins/flow-next/scripts/smoke_test.sh (99 passing), plugins/flow-next/scripts/resolve-pr_smoke_test.sh (58 passing), bun x biome check app/apps/flow-next/page.tsx
- PRs: