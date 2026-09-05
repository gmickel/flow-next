# Make Flow-Next easier to understand and adopt

## Goal & Context

Apply the accepted messaging review across the public site and GitHub documentation. Visitors should understand what they install, how the host agent adapts the pipeline, and what evidence they receive before adopting a larger workflow. All new copy is drafted under the prose skill and documentation contract.

## Architecture & Data Models

Keep the current Astro/Starlight site and plugin docs. The site owns the reading journey; repository docs own offline reference. Share the category, outcome headings, capability explanations, and example facts across both surfaces. Derive machine-readable discovery from current published pages where practical.

## API Contracts

Preserve existing public routes and heading anchors when reorganizing prose. Refresh page metadata, social metadata, structured data, sitemap, robots, and llms.txt. No plugin behavior or CLI contract changes.

## Edge Cases & Constraints

Keep the maintainer-confirmed 38-PR account and current homepage capability claims. Describe malleability positively. Historical release notes stay historical. New-user instructions distinguish shell commands from harness invocations. Preserve private-domain boundaries and existing quotes.

## Acceptance Criteria

- **R1:** Homepage and README explain the installed product, show plain-language routing, and connect an actual requirement, review correction, verification, and PR. No invented measured results.
- **R2:** Introduction and first-run guide give a concrete starting path with prerequisites, supported invocation forms, and inspectable output. Migration detail remains reachable without leading the first run.
- **R3:** Site and GitHub guides align on team adoption, costs, retained knowledge, current layout, and recommended autonomy. Existing links keep resolving.
- **R4:** Search and agent discovery surfaces describe the current content, expose canonical URLs, and resolve to built pages. No stale redirects in canonical discovery listings.
- **R5:** Site build, internal links, SEO checks, repo lint, anchors, mirror regeneration twice, and full tests pass. G1 and G2 apply.

## Boundaries

No new runtime dependency, plugin feature, model benchmark, or version bump. No client names or private implementation details. No prose sentence pins.

## Decision Context

Keep the strong headline and existing visual design. Make the product and its malleability concrete through examples and a shorter first-run journey. The homepage account is authoritative for the field case, as explicitly confirmed by the maintainer. The apparent duplicate Grounding Snapshot heading is an example inside a code fence and needs no correction.
