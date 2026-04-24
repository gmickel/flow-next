# fn-29-review-rigor-bundle.5 Protected artifacts path list in review prompts

## Description

Add a hardcoded never-flag path list to review prompts. Any finding recommending deletion, gitignore, or removal of files under these paths is discarded during synthesis. Prevents reviewer (especially external models unfamiliar with flow-next conventions) from suggesting destructive cleanups of `.flow/` state or Ralph harness files.

**Size:** XS (prompt-only)

**Files:**
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md`
- `plugins/flow-next/skills/flow-next-epic-review/workflow.md`
- `plugins/flow-next/skills/flow-next-plan-review/` (if review prompt exists — check and add)

## Change details

### Review prompts

Add near the top of the review prompt (before findings synthesis):

```markdown
## Protected artifacts

The following paths are flow-next / project-pipeline artifacts. Any finding recommending their deletion, gitignore, or removal MUST be discarded during synthesis. Do not flag these paths for cleanup under any circumstances:

- `.flow/*` — flow-next state, specs, tasks, epics, runtime
- `.flow/bin/*` — bundled flowctl
- `.flow/memory/*` — learnings store
- `.flow/specs/*.md` — epic specs (decision artifacts)
- `.flow/tasks/*.md` — task specs (decision artifacts)
- `docs/plans/*` — plan artifacts (if project uses this convention)
- `docs/solutions/*` — solutions artifacts (if project uses this convention)
- `scripts/ralph/*` — Ralph harness (when present)

These files are intentionally committed. They are the pipeline's state, not clutter. An agent that deletes them destroys the project's planning trail and breaks Ralph autonomous runs.

If you notice genuine issues with content INSIDE these files (e.g., a spec that contradicts itself, a runtime state that's stale), flag the content — not the file's existence.
```

### plan-review prompt (if it exists as separate file)

Same block. plan-review reviews plan documents; same protection applies.

### Synthesis discipline

Add a rule at the findings-merge step:

> **Protected-path filter.** Before emitting findings, scan each for recommendations to delete, gitignore, or rm-rf any path matching the protected list above. Drop those findings. Log drop count in the review output ("Protected-path filter: dropped N findings").

## Rationale

This is a safety rail, not a feature. External reviewers (codex/copilot running on an unfamiliar project) look at `.flow/` JSONs and naturally suggest "why are these committed?" Ralph in autofix mode could then apply that finding and destroy its own state. MergeFoundry upstream's protected-artifacts rule caught this failure mode; flow-next needs the same.

## Acceptance

- **AC1:** impl-review and epic-review workflow prompts contain the protected-paths list.
- **AC2:** plan-review (if present) contains the same list.
- **AC3:** Review synthesis step drops findings recommending deletion of protected paths.
- **AC4:** A synthetic test where the reviewer is given a diff including `.flow/*.json` files produces no deletion/gitignore finding in the output.
- **AC5:** Drop count (if any) is reported transparently in the review output.

## Out of scope

- Runtime enforcement (flowctl blocking rm of `.flow/*`) — this is a review-prompt discipline, not a hook.
- User-configurable protected paths — list is hardcoded for the plugin's use case.

## Done summary
Added hardcoded protected-artifacts path list (.flow/*, .flow/memory/*, .flow/specs/*.md, .flow/tasks/*.md, docs/plans/*, docs/solutions/*, scripts/ralph/*) to all three review prompts (impl-review, epic-review, plan-review) plus quality-auditor agent. Shared PROTECTED_ARTIFACTS_BLOCK constant in flowctl.py injected into build_review_prompt (impl + plan), build_standalone_review_prompt, and build_completion_review_prompt so rp/codex/copilot backends all discard findings recommending deletion/gitignore/removal of those paths and surface drop count via a "Protected-path filter:" line. .flow/bin/flowctl.py synced; Codex mirror regenerated via sync-codex.sh.
## Evidence
- Commits: c27f606150168e9f0442eea4e4592437f22df89a
- Tests: plugins/flow-next/scripts/smoke_test.sh (69/69 passed), python3 prompt-builder checks: build_review_prompt (impl + plan), build_standalone_review_prompt, build_completion_review_prompt all include Protected artifacts block, parse_suppressed_count + parse_classification_counts + parse_codex_verdict still parse correctly with Protected-path filter line present
- PRs: