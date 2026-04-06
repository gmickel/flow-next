# fn-26-designmd-aware-orchestration.1 Scout detection + plan skill: DESIGN.md → design context in task specs

## Description
Add DESIGN.md detection to repo-scout and conditional `## Design context` section to plan skill task spec template. This is the core detection-to-injection pipeline.

**Size:** M
**Files:** `plugins/flow-next/agents/repo-scout.md`, `plugins/flow-next/skills/flow-next-plan/steps.md`

## repo-scout changes

In repo-scout.md, add DESIGN.md to the "Project docs first" scan list (line 18-20):

```markdown
1. **Project docs first** (fast context)
   - CLAUDE.md, README.md, CONTRIBUTING.md, ARCHITECTURE.md, DESIGN.md
```

Add a conditional output section after "Reusable Code" in the output format:

```markdown
### Design System (if DESIGN.md found)
- Location: `DESIGN.md` (or `.stitch/DESIGN.md`)
- Colors: [key palette summary — primary, secondary, accent hex codes]
- Typography: [font families, key sizes]
- Components: [available component patterns]
- Status: [well-formed / partial / likely architecture doc not design system]
```

**Validation heuristic:** A file is a Stitch DESIGN.md (not an architecture design doc) if it has 3+ of these section headings (case-insensitive substring match): Overview, Colors, Color Palette, Typography, Elevation, Depth, Components, Component Stylings, Layout, Do's and Don'ts — AND contains at least 3 hex color codes (`#[0-9A-Fa-f]{3,8}`).

## Plan skill changes

In steps.md, add DESIGN.md awareness at two points:

**Step 1 (research captures, line ~118-127):** Add to the "Must capture" list:
```markdown
- DESIGN.md design system tokens (if repo-scout found one)
```

**Task spec template (line ~289-314):** Add conditional `## Design context` section between `## Investigation targets` and `## Key context`:

```markdown
## Design context
*Only include for frontend tasks when DESIGN.md exists in project.*

Relevant DESIGN.md sections for this task:
- **Colors:** Primary (#2665fd) for CTAs, Neutral (#757681) for backgrounds
- **Components:** Buttons are rounded (8px), primary uses brand blue fill
- **Do's/Don'ts:** Primary color only for single most important action per screen

Full design system: `DESIGN.md` (read before implementing UI changes)
```

**Frontend detection rule** (add as a planning note after task spec template):
```markdown
**Design context rule:** Only add `## Design context` to tasks where Files/Description reference frontend patterns:
- Extensions: .jsx, .tsx, .vue, .svelte, .css, .scss
- Directories: components/, pages/, views/, layouts/, styles/, app/
- Keywords: button, modal, form, layout, responsive, color, font, card, navigation, theme, UI, component

Backend-only tasks (api/, server/, controllers/, .py, .go): skip design context.
When ambiguous: include it (false positive is low-cost, false negative causes inconsistency).
```

## Investigation targets
**Required:**
- `plugins/flow-next/agents/repo-scout.md:17-20` — project docs scan list
- `plugins/flow-next/agents/repo-scout.md:52-74` — output format
- `plugins/flow-next/skills/flow-next-plan/steps.md:118-127` — must capture list
- `plugins/flow-next/skills/flow-next-plan/steps.md:289-314` — task spec template

## Key context
- repo-scout already scans CLAUDE.md, README.md, CONTRIBUTING.md, ARCHITECTURE.md — DESIGN.md fits the same pattern
- Task spec template already has Investigation targets and Key context sections — Design context slots between them
- The planner already runs scouts in Step 1 that produce findings — design tokens are just another finding type
- DESIGN.md files are compact (~2-5k tokens) — extracting key tokens into the design context section keeps task specs lean
## Acceptance
- [ ] repo-scout scans for DESIGN.md in project docs step
- [ ] repo-scout validates DESIGN.md (section headings + hex codes heuristic)
- [ ] repo-scout output includes Design System section when found
- [ ] repo-scout distinguishes Stitch DESIGN.md from architecture design docs
- [ ] Plan skill captures DESIGN.md tokens from scout output
- [ ] Plan skill writes `## Design context` for frontend tasks when DESIGN.md exists
- [ ] Plan skill skips design context for backend-only tasks
- [ ] Frontend detection heuristic documented (extensions, directories, keywords)
- [ ] Ambiguous tasks default to including design context
## Done summary
Added DESIGN.md detection to repo-scout (project docs scan, conditional Design System output, validation heuristic) and conditional ## Design context section to plan skill task spec template with frontend detection rule.
## Evidence
- Commits: d7262ed40236b18d118272cda86ad68fd3964d14
- Tests: plugins/flow-next/scripts/smoke_test.sh (52/52 pass)
- PRs: