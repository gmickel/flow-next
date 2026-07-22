---
satisfies: [R5]
---
# fn-125-cursor-scout-pin-wiring-consume-the.4 Regenerate mirror, publish docs, live-Cursor dogfood

## Description
Regenerate the Codex mirror, publish docs, and run the live-Cursor dogfood. Add a sync-codex.sh guard so the shared reference + caller contracts survive mirror generation WITHOUT applying Cursor pins on Codex; regenerate codex/references/read-only-scout-routing.md + codex/skills/flow-next-plan/steps.md + codex/skills/flow-next-prime/{SKILL,workflow}.md + codex/skills/flow-next-setup/workflow.md + codex/templates/usage.md. CHANGELOG `## Unreleased` fix. Downstream flow-next.dev: orchestration/index.mdx, install.mdx, subagents/overview.mdx, skills/setup.mdx, releases/changelog.mdx. NO version bump.

## Acceptance
- Codex mirror keeps its generated model-tier behavior; Cursor scout-routing branch inapplicable there.
- sync-codex.sh twice-idempotent (byte-identical 2nd pass); canonical/mirror tests prove zero Claude Code behavior change.
- Root + docs-site changelogs under Unreleased; no version manifests / FLOW_NEXT_VERSION / bump.sh.
- Full gate green (run_tests_parallel); flow-next.dev pnpm build green.
- NEEDS-HUMAN live-Cursor smoke: session=Terra, AGENTS.md scout pin=composer-2.5-fast; run /flow-next:plan + /flow-next:prime; Cursor child-run model metadata shows the pinned model for every eligible scout (NOT Terra). Record requested+observed model names; prompt text is NOT proof.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
