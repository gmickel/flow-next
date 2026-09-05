---
satisfies: [R4, R5]
---
# fn-222-make-flow-next-easier-to-understand-and.2 Refresh search and agent discovery and verify the combined change

## Description
Own site metadata, llms discovery, SEO validation, generated mirror and final gates. Check sitemap, canonical, social and structured data against actual routes; finish both repositories and receipts.

## Acceptance
R4-R5 hold; all required gates pass and source/mirror/site claims align.

## Done summary
Published-page discovery now follows the docs collection and navigation. The generated llms.txt lists all 83 docs pages; per-page social metadata and structured data describe each page. The discovery check validates all 84 content pages against canonical URLs, metadata, sitemap membership, robots, and the docs inventory, and rejects obsolete sitemap entries. The link check also validates downloadable examples. The site README documents how to keep these surfaces current.

Validation passed: site typecheck/build, 127-route link check, 84-page discovery check, Python tutorial baseline, desktop/mobile browser navigation, all nine shared outcome headings, retained page anchors, Codex regeneration twice, repo anchors, Ruff, and the full suite of 4,741 tests across 203 files with seven skips. The first full run exposed three removed README references, which were restored. A subsequent run hit /tmp quota errors; the final successful full run used TMPDIR=/home/gordon/.cache/flow-next-messaging-tests.

Site commits bd477f0 and 98b8c47; repository docs aaebdabb. Commits remain local. No plugin behavior or version changed.
## Evidence
- Commits: aaebdabb
- Tests: TMPDIR=/home/gordon/.cache/flow-next-messaging-tests python3 scripts/run_tests_parallel.py: 4741 tests, 203 files, 7 skipped, zero failures or errors, uvx ruff@0.16.0 check ., python3 scripts/check_doc_anchors.py, ./scripts/sync-codex.sh twice, pnpm build (flow-next.dev), pnpm check:links: 127 routes, pnpm check:seo: 84 pages and 83 docs entries, Desktop/mobile agent-browser checks and tutorial download, Shared nine outcome headings and changed-page anchor retention
- PRs: