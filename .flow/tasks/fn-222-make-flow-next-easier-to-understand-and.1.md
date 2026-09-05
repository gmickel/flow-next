---
satisfies: [R1, R2, R3]
---
# fn-222-make-flow-next-easier-to-understand-and.1 Update messaging and onboarding across site and repository docs

## Description
Apply the accepted review with prose-skill drafting. Own README.md, plugins/flow-next/docs, site landing and guide content. Preserve anchors, actual example evidence, headline and approved field-case facts.

## Acceptance
R1-R3 hold across both surfaces; examples are sourced, first run reproducible, team and cost guidance practical.

## Done summary
Updated the website and repository docs so visitors can identify the plugin, choose a workflow, try a concrete two-file example, and follow a real review correction into PR #215. Aligned team adoption, agent costs, knowledge continuity, current installation layout, and autonomous handovers. Preserved the maintainer-confirmed 38-PR field case and existing anchors. Drafted copy under the prose skill.

Website commits: bd477f0 and 98b8c47. Repository documentation: aaebdabb. Site build, 127-route link check, 84-page discovery check, tutorial baseline, focused documentation tests, lint, and anchors pass. Desktop and mobile browser checks covered the homepage example, linked article, first-run page, and example download. Full suite verification is recorded by the final task.
## Evidence
- Commits: aaebdabb
- Tests: pnpm build (flow-next.dev), pnpm check:links (127 routes), pnpm check:seo (84 pages), python3 -m unittest -v (export-json starter), python3 -m unittest discover -s plugins/flow-next/tests -p test_chart_docs_inventory.py -q, python3 -m unittest discover -s plugins/flow-next/tests -p test_review_findings_docs.py -q, uvx ruff@0.16.0 check ., python3 scripts/check_doc_anchors.py, agent-browser desktop and mobile navigation and download checks
- PRs: