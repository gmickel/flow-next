---
satisfies: [R19, R30, R31, R32, R33, R34, R49, R51, R52, R53, R54, R55]
---
# fn-135-chart-decision-map-discovery-for.8 Publish public chart docs and cookbook journeys

## Description
### Objective

Update the public `flow-next.dev` documentation in its own clean worktree, including the full chart page, both navigation sources, pipeline routing, configuration/CLI reference, adjacent skill boundaries, autonomy/team guidance, glossary/changelog, and cookbook examples.

### Worktree boundary

The current `~/work/flow-next.dev` checkout may contain unrelated work. Create a separate worktree/branch for this task, preserve existing changes, commit this docs-site change separately, and report that commit as evidence for fn-135.

Before editing, re-read the landed fn-147 docs commit and fn-148's final report/current landed template guidance. Preserve fn-147's two evidence/source-tag cookbook recipes and interview-page semantics. A planned, NOT CONFIRMED, or INCONCLUSIVE fn-148 outcome adds no public claim; consume verified/inferred fact guidance only when its exact human-approved diff has landed.

### Exact files

- New `src/content/docs/skills/chart.mdx`.
- New `src/content/docs/skills/guide.mdx` — the router shipped by task 6 gets its own public page; a skill missing from the navs silently vanishes.
- `astro.config.mjs` and `src/lib/site.ts` — add Chart between Prospect and Capture, and Guide before Prospect, in both independent navs.
- `src/content/docs/strategy/pipeline.mdx`, `when-to-use.mdx`, `menu-not-a-rail.mdx`, `prototype-driven-specs.mdx`.
- `src/content/docs/cookbook.mdx`, `first-30-minutes.mdx`, `introduction.mdx`.
- `src/content/docs/flowctl/commands.mdx`, `cli-reference.mdx`, `configuration.mdx`.
- `src/content/docs/specs/writing-specs.mdx`.
- `src/content/docs/skills/index.mdx`, `prospect.mdx`, `capture.mdx`, `interview.mdx`, `plan.mdx`, `pilot.mdx`.
- `src/content/docs/teams/collaboration.mdx`, `orchestration/index.mdx`, `autonomous/overview.mdx`.
- `src/content/docs/teams/tracker-sync.mdx`.
- `src/content/docs/reference/glossary.mdx`, `releases/changelog.mdx`.

Do not alter the homepage build-loop mock; it depicts post-spec execution. Change homepage marketing copy only if it makes an externally false pipeline claim after the docs update.

### Cookbook requirements

Give each journey a concrete prompt, compact chart state, next decision, evidence/consent boundary, re-chart result, and handoff:

1. **Skip chart:** a clear local change routes directly to capture/direct work with the reason chart adds no signal.
2. **Research-led:** a bounded Grounding Snapshot cites known repo/domain evidence without manufacturing decisions; two independent unattended questions fan out, one answer makes a new decision stateable, and the route adapts.
3. **Prototype reversal:** a scoped throwaway artefact is created/imported, attached with stable reference/revision while the D-ID stays open, presented to the human, and resolved only after the recorded reaction. The old assumption is preserved/superseded, dependent work is redrawn, and the briefing retains the artefact reference.
4. **Multi-spec briefing:** resolved decisions reveal two genuine boundaries, shared context is named once, confirmation precedes two capture handoffs.
5. **Tracker re-entry:** a pasted projected parent URL re-anchors on local chart status/frontier and a decision URL selects the exact open D-ID; an unsupported/unlinked/historical URL fails visibly or shows history and offers the local chart-id/frontier path without guessing.

Use flow-next chart vocabulary and original approximated examples. State explicitly that these are possible traces, not phases.

### Public narrative requirements

- Chart is an optional high-fog on-ramp before capture; preserve the lightweight first-run happy path.
- One smallest-sufficient matrix covers direct change, prospect, chart, capture/direct spec, interview, plan, work, review/QA/ship.
- Prompt-first language leads; exact CLI/flags/config/error/result contracts remain complete in reference pages.
- Explain attended/unattended automation boundaries and `.flow/` canonical/tracker projection. D-ID/evidence provenance remains separate from acceptance-criterion source tags; chart hands off through capture without implying capture is the only criterion-tag writer.
- Explain bounded grounding in the chart page, first-30-minutes, and cookbook: prompt plus known evidence -> safe cited snapshot -> Outcome/frontier/cost read-back -> persist nothing until confirmed. Conflicting/stale/unavailable evidence stays uncertainty; chart creation resolves nothing.
- Explain the tracker lifecycle in the chart page, tracker-sync page, and CLI references: decision type/attendance/status/blocking/safe evidence, projection-only parent counts/latest resolution/frontier/chart status, explicit provider degradation, and local-first revisioned retry/reconcile receipts.
- Document supported pasted tracker URL re-entry as a convenience resolved through the local provenance ledger, never remote search/title matching or canonical state. Parent/open-decision/history/failure examples must read back the canonical local ID/title/link.
- Add public glossary terms and append under the existing `## Unreleased`; retain fn-147 and other pending entries; no version bump.

### Quick commands

```bash
pnpm check
pnpm build
```

### Non-goals

- No product code or plugin generated files in the docs repo.
- No chart-level verified/inferred fact or decision grammar ahead of a landed human-approved fn-148 result.

## Acceptance
- Complete public chart and guide pages ship; both independent nav sources place Chart between Prospect and Capture and Guide before Prospect.
- Pipeline, when-to-use, menu, prototype doctrine, first-run, CLI/config, spec, skill-boundary, team, orchestration/autonomy, glossary, and changelog pages agree on the optional prompt-first contract.
- Cookbook includes all five materially different original Flow-Next journeys with prompts, evidence/consent boundaries, adaptive re-charting, and no mandatory phase order.
- Grounding and prototype examples prove approved source references/revisions, no implicit decision resolution, persisted artefact before reaction, human-controlled resolution, interruption-safe resumption, supersession, and adaptive frontier redraw.
- Tracker docs define chart-parent/decision-child lifecycle rollups, type, attendance, status, safe evidence, explicit degradation, and reconcile-safe projection without making the tracker canonical.
- Supported chart/decision tracker URLs re-enter via the local locator ledger; unsupported, unlinked, stale, conflicting, or historical selectors fail/show history visibly and offer the local ID/frontier path without mutation or guessing.
- Cookbook/interview docs preserve fn-147's source-tag recipes and `untagged = unknown`, while chart examples retain D-ID/evidence references without relabelling facts or claiming an unlanded fn-148 outcome.
- Public `## Unreleased` entry exists, with no version bump.
- Work occurs in a separate clean flow-next.dev worktree and yields a separate commit for fn-135 evidence.
- `pnpm check` and `pnpm build` pass in that worktree.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
