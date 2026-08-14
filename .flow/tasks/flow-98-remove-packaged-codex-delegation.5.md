---
satisfies: [R4, R7, R10]
---
# flow-98-remove-packaged-codex-delegation.5 Docs sweep, CHANGELOG breaking-change entry, and the final gate

## Description
Point every doc that described packaged delegation at the prose route, confirm the per-spec backend fields survive untouched, and stage the breaking-change entry for the major release this ships in.

**Size:** M
**Files:** `plugins/flow-next/docs/orchestration.md`, `ralph.md`, `teams.md`, `flowctl.md`, `skills.md`, `docs/README.md`, repo `CLAUDE.md` (the delegation carve-out prose), `CHANGELOG.md`
**Touches:** [plugins/flow-next/docs/**, CLAUDE.md, CHANGELOG.md]

### Approach
- Sweep by grep, not by memory: find every mention of the removed vocabulary across canonical docs and the repo instruction file, and either delete it or repoint it at the bridge recipe plus the routing preference.
- The repo's own instruction file carries a sanctioned-carve-out paragraph naming delegation as the one licensed second-LLM spawn. That paragraph must be rewritten, not deleted: the carve-out list still has members (review dispatch, the triage-skip judge), and the sentence that names them is doctrine.
- Confirm and state that `spec set-backend`'s per-spec impl/review/sync fields are untouched - they are data carriage for other control planes, not delegation.
- CHANGELOG under `## Unreleased`, outcome-first, framed as a breaking change for the next major: what disappears, what replaces it, and the one-line migration. Say plainly that routing became a preference you write rather than a subsystem you configure. No benchmark tables, no speed claims.
- Full gate: the parallel suite with the exit code captured directly, plus the pinned linter. Mirror regenerated twice.

### Investigation targets
**Required** (read before coding):
- repo `CLAUDE.md` sanctioned-carve-out paragraph - rewrite target, not a delete target
- `plugins/flow-next/docs/orchestration.md` delegation sections - the largest doc surface
- `agent_docs/releasing.md` - the changelog register and the breaking-change requirement for a major

### Acceptance
- [ ] No canonical doc or repo instruction file describes packaged delegation as available; each mention deleted or repointed
- [ ] The sanctioned-carve-out paragraph rewritten with its remaining members, not removed
- [ ] `spec set-backend` fields verified untouched and stated as such in the summary
- [ ] `## Unreleased` CHANGELOG entry, outcome-first, marked breaking, with the migration line; no version bump
- [ ] Mirror regenerated twice (idempotent); full suite + linter green with exit codes captured directly

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
