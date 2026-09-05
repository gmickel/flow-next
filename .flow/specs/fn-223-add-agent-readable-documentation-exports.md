# Agent-readable documentation exports

## Goal
Agents can retrieve the relevant Flow-Next documentation as Markdown, or fetch the full collection, using links exposed by the website.

## Approach
Generate Markdown from rendered documentation HTML during the site build. Preserve rendered components, code blocks, tables, hidden tab panels, details, and image descriptions. Keep canonical source URLs and absolute links. Add page-level alternate and describedby links, update llms.txt, and validate the exported inventory and content.

## Acceptance Criteria
- R1: Every published docs page has a clean Markdown export preserving its rendered content; redirects and the error page are excluded.
- R2: llms.txt links to individual exports and llms-full.txt; HTML docs advertise their Markdown alternate and the index.
- R3: Component conversion tests, the site build, links, discovery checks, and local HTTP checks pass. HTML Accept requests remain non-failing. Document the static build and retrieval behavior.

## Boundaries
Site-only implementation. No plugin behavior, version change, runtime content negotiation, deployment, or search ranking claim. New copy follows the prose skill. Existing unrelated repository changes remain untouched.
