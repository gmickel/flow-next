---
satisfies: [R8, R9, R10, R11]
---
# fn-145-opus-5-autonomous-seam-retune.4 Regenerate, verify, land, and update downstream docs

## Description
Regenerate cross-platform artifacts, record the retune, run the complete gate,
and prepare the spec-derived branch for completion review and PR creation.
Landing, the public docs-site update, and the concurrent-branch coordination
prompt are immediate post-task lifecycle actions because their evidence exists
only after this task and the completion-review gate are done.

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
- Leave a precise downstream file/build handoff for flow-next.dev.
- After this task reaches done, the conductor runs completion review,
  spec-derived make-pr, the normal bounded land procedure, then applies and
  verifies the downstream update.
- Only after merge, produce a self-contained prompt naming the actual main
  commit, overlapping paths, gates, and inspect-before-rebase guidance.

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
branch, test, PR, and landing rules. Neither its landing evidence nor the
coordination prompt can exist before the main PR merge; they are spec-run
follow-ups, not preconditions for marking this implementation task done.
## Acceptance
- [ ] Canonical changes and generated Codex mirror are aligned; two consecutive
  sync runs are clean/idempotent.
- [ ] Repo Unreleased changelog records the behavior change without a version
  bump; optimization log records only measured evidence.
- [ ] Focused suites, full parallel tests, Ruff 0.16.0, and relevant smokes pass.
- [ ] Branch is clean and ready for the mandatory completion review and
  spec-derived make-pr workflow.
- [ ] Exact flow-next.dev files, copy, and documented verification command are
  captured for the post-main-merge downstream update.
- [ ] Post-task handoff explicitly requires normal landing, downstream
  verification/landing, and a final concurrent-agent prompt using the actual
  main merge commit and overlap set.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
