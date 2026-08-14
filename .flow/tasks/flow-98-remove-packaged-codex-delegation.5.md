---
satisfies: [R4, R7, R10]
---
# flow-98-remove-packaged-codex-delegation.5 Docs sweep, CHANGELOG breaking-change entry, and the final gate

## Description
Point every doc that described packaged delegation at the prose route, confirm the per-spec backend fields survive untouched, and stage the breaking-change entry for the major release this ships in.

**Size:** M
**Files:** `plugins/flow-next/docs/orchestration.md`, `ralph.md`, `teams.md`, `flowctl.md`, `skills.md`, `docs/README.md`, repo `CLAUDE.md` (the delegation carve-out prose), `CHANGELOG.md`, `plugins/flow-next/skills/flow-next-impl-review/workflow-common.md` (dangling `references/codex-delegation.md` pointer at the foreground-rule note), `plugins/flow-next/skills/flow-next-qa/workflow.md` (same dangling pointer at the never-subtract note), `plugins/flow-next/skills/flow-next-setup/workflow.md` + its `references/model-routing-question-{cursor,grok,bridge}.md` (the `Scaffold + enable codex delegation` option and `HAVE_CODEX`-gated delegation wiring), `plugins/flow-next/scripts/flowctl.py` (orphaned `codex classify-result` / `codex rollback-plan` subcommands — the classify-judge CLI surface .2 didn't own)
**Touches:** [plugins/flow-next/docs/orchestration.md, plugins/flow-next/docs/ralph.md, plugins/flow-next/docs/teams.md, plugins/flow-next/docs/flowctl.md, plugins/flow-next/docs/skills.md, plugins/flow-next/docs/README.md, CLAUDE.md, CHANGELOG.md, .flow/usage.md, .flow/bin/**, plugins/flow-next/skills/flow-next-impl-review/workflow-common.md, plugins/flow-next/skills/flow-next-qa/workflow.md, plugins/flow-next/skills/flow-next-setup/**, plugins/flow-next/scripts/flowctl.py]

<!-- Updated by plan-sync: fn-98.2 done-summary review surfaced 4 dangling references the earlier Files/Touches list didn't name — added here rather than left implicit under "sweep by grep" -->


### Approach
- Sweep by grep, not by memory: find every mention of the removed vocabulary across canonical docs and the repo instruction file, and either delete it or repoint it at the bridge recipe plus the routing preference. This sweep is not docs-tree-only: two skill workflow files carry a dangling pointer at `references/codex-delegation.md` (deleted in .2) — `flow-next-impl-review/workflow-common.md`'s foreground-rule note and `flow-next-qa/workflow.md`'s never-subtract note — reword both, do not just drop the dead link.
- `flow-next-setup/workflow.md` Step 6d still offers `Scaffold + enable codex delegation` as a Model Routing option (gated on `HAVE_CODEX=1`), and its `references/model-routing-question-{cursor,grok,bridge}.md` wire the same option through. Remove the delegation branch from the frozen option set and from each reference; the remaining options (`Scaffold` / `Skip`) are unaffected.
- `flowctl.py` still carries the `codex classify-result` / `codex rollback-plan` subcommands that backed the classify judge's CLI surface — .2 removed the skill-prose caller (Phase 1.5) but not this implementation. Zero callers remain after .2; delete them here as part of the full-gate propagation pass, and check the schema/help text for matching entries.
- The repo's own instruction file carries a sanctioned-carve-out paragraph naming delegation as the one licensed second-LLM spawn. That paragraph must be rewritten, not deleted: the carve-out list still has members (review dispatch, the triage-skip judge), and the sentence that names them is doctrine.
- Confirm and state that `spec set-backend`'s per-spec impl/review/sync fields are untouched - they are data carriage for other control planes, not delegation.
- CHANGELOG under `## Unreleased`, outcome-first, framed as a breaking change for the next major: what disappears, what replaces it, and the one-line migration. Say plainly that routing became a preference you write rather than a subsystem you configure. No benchmark tables, no speed claims.
- **This task owns ALL propagation for the spec** (the earlier tasks deliberately skip it so they can wave): copy the module to the dogfood bin, regenerate the manifest, sync the mirror twice, and confirm the tree is clean.
- Full gate: the parallel suite with the exit code captured directly, plus the pinned linter.

### Investigation targets
**Required** (read before coding):
- repo `CLAUDE.md` sanctioned-carve-out paragraph - rewrite target, not a delete target
- `plugins/flow-next/docs/orchestration.md` delegation sections - the largest doc surface
- `agent_docs/releasing.md` - the changelog register and the breaking-change requirement for a major
- `plugins/flow-next/skills/flow-next-impl-review/workflow-common.md` ~line 96 and `plugins/flow-next/skills/flow-next-qa/workflow.md` ~line 208 - dangling `codex-delegation.md` pointers (fn-98.2 done-summary review)
- `plugins/flow-next/skills/flow-next-setup/workflow.md` Step 6d + `references/model-routing-question-{cursor,grok,bridge}.md` - the `Scaffold + enable codex delegation` option
- `plugins/flow-next/scripts/flowctl.py` `codex classify-result` / `codex rollback-plan` - orphaned CLI surface, zero callers since .2

### Acceptance
- [ ] No canonical doc or repo instruction file describes packaged delegation as available; each mention deleted or repointed
- [ ] `workflow-common.md`'s and `flow-next-qa/workflow.md`'s dangling `codex-delegation.md` pointers reworded, not just unlinked
- [ ] `flow-next-setup`'s Model Routing question and its per-platform references carry no `Scaffold + enable codex delegation` option
- [ ] `flowctl.py`'s `codex classify-result` / `codex rollback-plan` subcommands removed (zero callers since .2); help text and schema checked for matching entries
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
