# fn-65-land-accept-a-bot-reviewed-clean.2 Docs (flowctl.md + flow-next.dev land.mdx) + CHANGELOG + version bump + docs-site changelog

## Description
### Goal
Document the new clean-review-comment behavior across both doc surfaces, add the CHANGELOG entry, and bump the version. Satisfies the remainder of R6.

### Investigation targets
- `plugins/flow-next/docs/flowctl.md` (land config table ~:570-575) — add a `land.cleanReviewCommentPattern` row. **Show the default as the built-in structured ERE (NOT `""`), and state explicitly: "set to an empty string to disable the comment scan."** Verbose style matching the `land.reviewTrigger` row; cross-ref `(fn-65)`.
- flow-next.dev `~/work/flow-next.dev/src/content/docs/autonomous/land.mdx` — THREE touchpoints: (1) the `silence` row in the review-signal table (~:82) — append "…or a bot comment matching `land.cleanReviewCommentPattern` that names the current head SHA"; (2) the automated-reviewer prose (~:86); (3) the Configuration table (~:94-99) — new key row, same default/empty-disables wording.
- `CHANGELOG.md` — new `## [flow-next X.Y.Z]` entry (land behavior + new config key + new code path → version bump). `### Added`, bold feature + `(fn-65)` citation. Run `scripts/bump.sh <patch|minor> flow-next` (patch likely — additive, opt-in, backward-compatible).
- flow-next.dev: `src/content/docs/releases/changelog.mdx` (newest-at-top `## Latest`, per agent_docs/releasing.md format), bump `src/lib/site.ts` `FLOW_NEXT_VERSION` + `package.json`. Run `pnpm build`; commit separately in the flow-next.dev repo.

### Notes
SKILL.md + the canonical land workflow prose are owned by fn-65.1 (so the Codex mirror regen happens once there). This task is the NON-skill docs (flowctl.md, flow-next.dev) + CHANGELOG + version bump only — no land skill prose, no second mirror regen.
## Acceptance
- [ ] flowctl.md land config table documents `land.cleanReviewCommentPattern` — default shown as the **built-in structured ERE** (not `""`), with "set to empty string to disable the comment scan" stated explicitly.
- [ ] flow-next.dev land.mdx updated in all three spots (silence-signal table row, automated-reviewer prose, Configuration table — same default/empty-disables wording); `pnpm build` green; committed in the flow-next.dev repo.
- [ ] CHANGELOG.md entry added + version bumped via `scripts/bump.sh` across all manifests; flow-next.dev changelog + `FLOW_NEXT_VERSION` + package.json bumped to match.
- [ ] Repo gate green (`bash plugins/flow-next/tests/ci_test.sh`).
## Done summary
Documented the new `land.cleanReviewCommentPattern` config key in flowctl.md (land config table — default shown as the built-in structured ERE, with empty-string-disables stated), added a CHANGELOG 2.1.1 `### Added` entry citing fn-65, and bumped the version 2.1.0 -> 2.1.1 across all manifests + README badge via scripts/bump.sh. RepoPrompt impl-review: SHIP, no findings; repo gate green (67/0).
## Evidence
- Commits: dd2da711612bc5bbf0d7df4f61ea2dc4707a8146
- Tests: bash plugins/flow-next/scripts/ci_test.sh (67 passed, 0 failed)
- PRs: