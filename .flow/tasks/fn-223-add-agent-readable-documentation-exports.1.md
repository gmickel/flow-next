# fn-223-add-agent-readable-documentation-exports.1 Generate and verify Markdown documentation surfaces

## Description
Generate Markdown from the built docs HTML, expose individual and full exports through discovery links, and verify the rendered content and local HTTP behavior. Scope is the documentation site; preserve the plugin's runtime and version.

## Acceptance
- R1-R3 in the spec hold. The site build, converter tests, link and discovery checks, and HTTP checks pass.

## Done summary
Agents can retrieve all 83 published docs pages as Markdown or fetch llms-full.txt. The build converts rendered HTML, preserving recipe cards, tab labels and hidden panels, details, tables, exact code blocks, and screenshot descriptions. Each export names its canonical source and resolves links absolutely. The index links to the Markdown versions; HTML pages expose alternate and describedby links.

Implemented in flow-next.dev commit eff255f. No plugin code or version changed. Copy follows the prose skill. Site build, four converter tests, 127-route links, 84-page SEO/export validation, and HTTP checks for all 85 text resources passed. Missing exports return 404. The live HTML route still returns 200 HTML to a Markdown-only Accept request. Astro preview requires an HTML fallback in Accept for directory routes; README documents that difference and the static-build workflow. The explicit Markdown URLs work in preview with text/markdown responses.

The tests caught and corrected missing tab labels, screenshot images inside buttons, empty legacy anchors, and code verification within blockquotes. All rendered code blocks and images now pass export checks. Changes remain committed locally, without deployment.
## Evidence
- Commits: eff255f
- Tests: pnpm build (flow-next.dev), pnpm test: 4 passed, pnpm check:links: 127 routes, pnpm check:seo: 84 pages, 83 Markdown docs, pnpm check:http http://127.0.0.1:4391: 85 resources, content types, body parity, HTML fallback, and missing export, Live HTML route with Accept text/markdown: HTTP 200
- PRs: