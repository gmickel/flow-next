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
platforms.md Grok section: GROK_AGENT detection signal table, instruction-file probe (loads BOTH CLAUDE.md+AGENTS.md), slash syntax, copy mode, host review + single-family fail-closed note, no-Ralph (intentional), Droid-nesting NEEDS-HUMAN edge; stale codex-fallback claims corrected. CHANGELOG Unreleased fn-126 entry (plain hyphens, no bump). flow-next.dev: 6 existing pages updated (install/introduction/changelog/review-workflow/setup/architecture) + customer-register Unreleased entry, pnpm build green, committed separately (8561874). Command-discovery expected-fixed by fn-124 (3.3.1), live grok validation = NEEDS-HUMAN (recorded, not claimed). Vault Platforms note = release-time downstream (deferred to fn-126 release walk). grok-4.5 high (2 passes); reviewed by session model; no em dashes.
## Evidence
- Commits: 8872b744
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_cursor_docs_contract -q, cd ~/work/flow-next.dev && pnpm build
- PRs: