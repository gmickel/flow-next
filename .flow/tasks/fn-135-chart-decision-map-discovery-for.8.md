---
satisfies: [R19, R30, R31, R32, R33, R34]
---
# fn-135-chart-decision-map-discovery-for.8 Publish public chart docs and cookbook journeys

## Description
### Objective

Update the public `flow-next.dev` documentation in its own clean worktree, including the full chart page, both navigation sources, pipeline routing, configuration/CLI reference, adjacent skill boundaries, autonomy/team guidance, glossary/changelog, and cookbook examples.

### Worktree boundary

The current `~/work/flow-next.dev` checkout may contain unrelated work. Create a separate worktree/branch for this task, preserve existing changes, commit this docs-site change separately, and report that commit as evidence for fn-135.

### Exact files

- New `src/content/docs/skills/chart.mdx`.
- `astro.config.mjs` and `src/lib/site.ts` — add Chart between Prospect and Capture in both independent navs.
- `src/content/docs/strategy/pipeline.mdx`, `when-to-use.mdx`, `menu-not-a-rail.mdx`, `prototype-driven-specs.mdx`.
- `src/content/docs/cookbook.mdx`, `first-30-minutes.mdx`, `introduction.mdx`.
- `src/content/docs/flowctl/commands.mdx`, `cli-reference.mdx`, `configuration.mdx`.
- `src/content/docs/specs/writing-specs.mdx`.
- `src/content/docs/skills/index.mdx`, `prospect.mdx`, `capture.mdx`, `interview.mdx`, `plan.mdx`, `pilot.mdx`.
- `src/content/docs/teams/collaboration.mdx`, `orchestration/index.mdx`, `autonomous/overview.mdx`.
- `src/content/docs/reference/glossary.mdx`, `releases/changelog.mdx`.

Do not alter the homepage build-loop mock; it depicts post-spec execution. Change homepage marketing copy only if it makes an externally false pipeline claim after the docs update.

### Cookbook requirements

Give each journey a concrete prompt, compact chart state, next decision, evidence/consent boundary, re-chart result, and handoff:

1. **Skip chart:** a clear local change routes directly to capture/direct work with the reason chart adds no signal.
2. **Research-led:** two independent unattended questions fan out, one answer makes a new decision stateable, and the route adapts.
3. **Prototype reversal:** a human reacts to a throwaway artifact, the old assumption is preserved/superseded, and dependent work is redrawn.
4. **Multi-spec briefing:** resolved decisions reveal two genuine boundaries, shared context is named once, confirmation precedes two capture handoffs.

Use flow-next chart vocabulary and approximated examples, not source attribution or a copied foreign workflow. State explicitly that these are possible traces, not phases.

### Public narrative requirements

- Chart is an optional high-fog on-ramp before capture; preserve the lightweight first-run happy path.
- One smallest-sufficient matrix covers direct change, prospect, chart, capture/direct spec, interview, plan, work, review/QA/ship.
- Prompt-first language leads; exact CLI/flags/config/error/result contracts remain complete in reference pages.
- Explain attended/unattended automation boundaries and `.flow/` canonical/tracker projection.
- Add public glossary terms and `## Unreleased`; no version bump.

### Quick commands

```bash
pnpm check
pnpm build
```

### Non-goals

- No product code or plugin generated files in the docs repo.

## Acceptance
- A complete public chart page ships and both independent nav sources place it between Prospect and Capture.
- Pipeline, when-to-use, menu, prototype doctrine, first-run, CLI/config, spec, skill-boundary, team, orchestration/autonomy, glossary, and changelog pages agree on the optional prompt-first contract.
- Cookbook includes all four required materially different journeys with prompts, evidence/consent boundaries, adaptive re-charting, and no mandatory phase order or external source attribution.
- Public `## Unreleased` entry exists, with no version bump.
- Work occurs in a separate clean flow-next.dev worktree and yields a separate commit for fn-135 evidence.
- `pnpm check` and `pnpm build` pass in that worktree.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
