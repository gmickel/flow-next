# Plan strategy alignment sections

Load this reference only when the Step 1 strategy probe printed its sentinel
(`STRATEGY_PRESENT=true` — `sections_filled >= 1`). Repos with no STRATEGY.md,
or a husk (`sections_filled == 0`), skip both sections below entirely and never
reach this file.

Both sections belong in the Step 5 plan scaffold, between
`## Boundaries / non-goals` and `## Decision context`:

```
## Strategy Alignment
<!-- Include this section ONLY when STRATEGY_PRESENT=true from Step 1.
     When STRATEGY_PRESENT=false (no STRATEGY.md or husk: sections_filled == 0),
     skip this section entirely. -->

Active tracks served by this plan:
- **<track-name>** — <one line on how this plan advances the track>
- **<track-name>** — <one line>

<!-- If the plan serves no active strategy track, replace the bulleted list with: -->
_No active strategy track served — review for drift._

## Strategy drift flagged for review
<!-- Include this block ONLY when the plan scope conflicts with an active track.
     Mirrors plan-sync's "Decision overrides flagged for review" convention
     (agents/plan-sync.md). Read-only — the plan skill never auto-supersedes
     STRATEGY.md; the user (or `/flow-next:strategy`) decides whether to revise. -->

- **<track-name>**: <one line on how this plan diverges from the track's stated direction>. Review for revision via `/flow-next:strategy`.
```

**`## Strategy Alignment` rules (active iff STRATEGY_PRESENT=true from Step 1):**
- Section sits between `## Boundaries / non-goals` and `## Decision context` in the Step 5 template.
- List active tracks (`### <track-name>` blocks parsed from the strategy snapshot's `tracks` raw markdown string) that this plan advances.
- When the plan serves NO active track, render the placeholder `_No active strategy track served — review for drift._` literally — do not omit the section.
- Skip the entire section when STRATEGY_PRESENT=false. Husk-vs-presence: gated on `sections_filled >= 1`, NOT `[[ -f STRATEGY.md ]]`.

**`## Strategy drift flagged for review` rules (conditional on conflict detection):**
- Mirrors plan-sync's "Decision overrides flagged for review" surface (`agents/plan-sync.md` Phase 6 summary).
- Bulleted list with track name + plan-decision divergence + `Review for revision via /flow-next:strategy.` line per item.
- Read-only — the plan skill never edits STRATEGY.md, never marks a track superseded, never auto-supersedes anything. Surface for human review only.
- Omit the heading entirely when no drift detected. Empty drift block is silent, not `_(none)_`.
