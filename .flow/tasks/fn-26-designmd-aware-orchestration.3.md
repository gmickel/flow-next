# fn-26-designmd-aware-orchestration.3 Prime DC7 + docs-gap-scout: DESIGN.md readiness criterion

## Description
Add DESIGN.md readiness criterion to prime (Pillar 4) and DESIGN.md detection to docs-gap-scout.

**Size:** S
**Files:** `plugins/flow-next/skills/flow-next-prime/pillars.md`, `plugins/flow-next/agents/docs-gap-scout.md`

## Prime pillars.md changes

Add DC7 to Pillar 4 Documentation criteria table (after DC6, line 86):

```markdown
| DC7 | DESIGN.md exists (frontend projects) | DESIGN.md with color + typography + component sections (informational — not scored for backend-only projects) |
```

**Important:** DC7 is informational/advisory for projects without frontend code. Prime should note "DESIGN.md not found — recommended for projects with frontend UI" rather than marking it as a failure. This aligns with the "if present, use it" principle.

## docs-gap-scout changes

In docs-gap-scout.md, add DESIGN.md to the document location scan (around line 22 where it does `ls -la` checks):

```bash
ls -la DESIGN.md .stitch/DESIGN.md 2>/dev/null
```

Add to the output categories (around line 48):
```markdown
- Design system: DESIGN.md with design tokens (colors, typography, components)
```

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-prime/pillars.md:79-86` — DC1-DC6 table
- `plugins/flow-next/agents/docs-gap-scout.md:21-38` — scan commands
- `plugins/flow-next/agents/docs-gap-scout.md:45-50` — output categories

## Key context
- Pillar 4 has 6 criteria (DC1-DC6), scoring at 80%+ / 40-79% / <40% thresholds — adding DC7 changes the denominator from 6 to 7, so 80% goes from 5/6 to 6/7. This is fine since DC7 is informational for backend projects.
- docs-gap-scout already checks for `.storybook/`, `stories/`, ADRs — DESIGN.md fits the same scan pattern
- Keep DC7 description short — one row in the table, consistent with DC1-DC6 style
## Acceptance
- [ ] DC7 added to Pillar 4 criteria table in pillars.md
- [ ] DC7 is informational for backend-only projects
- [ ] docs-gap-scout scans for DESIGN.md and .stitch/DESIGN.md
- [ ] docs-gap-scout reports DESIGN.md in output categories
- [ ] Scoring thresholds still make sense with 7 criteria (80% = 6/7)
- [ ] No changes to prime workflow or scout dispatch
## Done summary
Added DC7 DESIGN.md criterion to Pillar 4 in pillars.md (informational for backend-only). Updated docs-gap-scout with DESIGN.md/.stitch/DESIGN.md scan, category entry, match table row, and output example.
## Evidence
- Commits: 1509dc4
- Tests: n/a — prompt-only changes
- PRs: