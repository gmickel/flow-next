---
satisfies: [R5]
---
# fn-126-grok-build-host-fidelity-positive.3 Docs walk + command-discovery validation + release staging

## Description
Downstream + command-discovery validation + release staging. Docs: plugins/flow-next/docs/platforms.md (Grok row/section: GROK_AGENT detection, slash syntax, canonical Claude files, copy mode, review incl. host with single-family fail-closed note, no-Ralph); flow-next.dev (install / platforms / introduction as relevant) + docs-site changelog `## Unreleased`; vault `flow-next - Platforms & Install.md` (reindex after). Command-discovery: fn-124 (command-shim flatten) has landed (3.3.1) - validate Grok's slash-menu discovery in a real grok session; record fixed-by-fn-124 or a linked residual follow-up (do NOT re-implement shim flattening here). CHANGELOG.md `## [Unreleased]`; NO version bump / FLOW_NEXT_VERSION / bump.sh. Covers R5.

## Acceptance
- platforms.md + flow-next.dev + vault note describe the Grok profile consistently; none claims CI proved live Grok behavior.
- Command-discovery validated post-fn-124 (NEEDS-HUMAN live grok check): recorded as fixed-by-fn-124 or a linked follow-up; no duplicate shim fix.
- Repo CHANGELOG `## [Unreleased]` + docs-site `## Unreleased`; no version manifests / FLOW_NEXT_VERSION / bump.sh touched.
- flow-next.dev `pnpm build` green; vault note reindexed + retrievable (maintainer-local, NEEDS-HUMAN).


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
