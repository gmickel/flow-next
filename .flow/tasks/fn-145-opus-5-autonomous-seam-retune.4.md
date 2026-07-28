---
satisfies: [R8, R9, R10, R11]
---
# fn-145-opus-5-autonomous-seam-retune.4 Regenerate, verify, land, and update downstream docs

## Description
Regenerate cross-platform artifacts, record the retune, run the complete gate,
land the spec-derived PR, update the public docs site after merge, and produce
the concurrent-branch coordination prompt from actual merge evidence.

**Size:** M

**Files:**
- `plugins/flow-next/codex/`
- `CHANGELOG.md`
- `agent_docs/optimization-log.md` when measured evidence exists
- downstream `/Users/gordon/work/flow-next.dev` Work/autonomy documentation

### Approach

- Regenerate the Codex mirror twice and inspect the introduced mirror diff.
- Add an Unreleased changelog note; no plugin version bump.
- Run focused suites, full parallel tests, pinned Ruff, and relevant smoke
  checks before PR creation.
- Use the spec-derived make-pr workflow and the normal bounded land procedure.
- After main merge, update flow-next.dev with the observable consent/continuation
  contract and verify its documented build.
- Produce a self-contained prompt naming the actual main commit, overlapping
  paths, gates, and inspect-before-rebase guidance for the concurrent agent.

### Investigation targets

**Required:**
- `scripts/sync-codex.sh`
- `CHANGELOG.md`
- `agent_docs/optimization-log.md`
- `agent_docs/releasing.md`
- `/Users/gordon/work/flow-next.dev/AGENTS.md` or project instructions
- `/Users/gordon/work/flow-next.dev/src/content/docs/skills/work.mdx`
- `/Users/gordon/work/flow-next.dev/src/content/docs/autonomous/overview.mdx`

**Optional:**
- `/Users/gordon/work/flow-next.dev/src/content/docs/skills/pilot.mdx`
- `/Users/gordon/work/flow-next.dev/src/content/docs/review/workflow.mdx`

### Key context

The docs site is a separate repository and must follow its own clean-worktree,
branch, test, PR, and landing rules. The coordination prompt cannot be finalized
until the main merge commit and overlap set are known.

## Acceptance
- [ ] Canonical changes and generated Codex mirror are aligned; two consecutive
  sync runs are clean/idempotent.
- [ ] Repo Unreleased changelog records the behavior change without a version
  bump; optimization log records only measured evidence.
- [ ] Focused suites, full parallel tests, Ruff 0.16.0, and relevant smokes pass.
- [ ] Spec-derived PR is created and merged through the normal landing
  procedure.
- [ ] flow-next.dev user-facing Work/autonomy truth surfaces are updated,
  verified, and landed under that repository's workflow.
- [ ] Final concurrent-agent prompt includes the actual main commit, overlap
  paths, verification evidence, and inspect/rebase guidance.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
