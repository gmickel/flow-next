# fn-26-designmd-aware-orchestration.4 Quality-auditor + flow-gap-analyst: conditional design checks

## Description
Add conditional design system checks to quality-auditor and flow-gap-analyst. Both are advisory — flag, never block.

**Size:** S
**Files:** `plugins/flow-next/agents/quality-auditor.md`, `plugins/flow-next/agents/flow-gap-analyst.md`

## quality-auditor changes

Add conditional Section 8 after Performance Red Flags (line 68):

```markdown
### 8. Design System Conformance (if DESIGN.md exists)

Skip this section if no DESIGN.md in project root.

If DESIGN.md exists and diff contains frontend files (.jsx, .tsx, .vue, .svelte, .css, .scss):
- **Hard-coded colors**: Check for hex codes (#xxx) in component files that should use design tokens
- **Hard-coded spacing**: Arbitrary pixel values where design system spacing scale exists
- **Missing token usage**: Components not referencing CSS variables / theme tokens when DESIGN.md defines them
- **Component drift**: UI patterns that diverge from DESIGN.md component specifications
- This is ADVISORY — design token adoption is gradual, don't block shipping
```

Add to output format after Test Budget section:

```markdown
### Design Conformance (if DESIGN.md present)
- Hard-coded values found: [list files with raw hex/px instead of tokens]
- Design token coverage: [% of UI changes using design system tokens]
- Advisory: [specific suggestions]
```

## flow-gap-analyst changes

Add conditional Section 6 after Integration Points (line 50):

```markdown
### 6. Design System Alignment (if DESIGN.md exists)

Skip if no DESIGN.md in project.

If DESIGN.md exists and the feature involves UI:
- Are the components needed for this feature defined in DESIGN.md?
- Do the color/spacing tokens in DESIGN.md cover this feature's needs?
- Are responsive breakpoints defined for the contexts this feature uses?
- Any design gaps that should be raised before implementation?
```

Add to output format after Integration Risks:

```markdown
### Design Gaps (if DESIGN.md present)
- [ ] [Missing component/token/breakpoint]: [What's needed]
```

## Investigation targets
**Required:**
- `plugins/flow-next/agents/quality-auditor.md:57-68` — performance section (insert after)
- `plugins/flow-next/agents/quality-auditor.md:96-108` — output format
- `plugins/flow-next/agents/flow-gap-analyst.md:45-50` — integration points (insert after)
- `plugins/flow-next/agents/flow-gap-analyst.md:52-81` — output format

## Key context
- Quality-auditor is read-only (disallowedTools: Edit, Write, Task) — reports only
- Flow-gap-analyst is read-only — asks questions, doesn't implement
- Both sections are conditional ("Skip if no DESIGN.md") — zero impact on projects without DESIGN.md
- Frontend file detection: same heuristic as plan skill (extensions + directories)
- Advisory only — "design token adoption is gradual" acknowledges mixed codebases
## Acceptance
- [ ] Quality-auditor has conditional Section 8 for design conformance
- [ ] Quality-auditor checks for hard-coded colors/spacing in frontend files
- [ ] Quality-auditor section skipped when no DESIGN.md exists
- [ ] Quality-auditor output format includes Design Conformance section
- [ ] Flow-gap-analyst has conditional Section 6 for design alignment
- [ ] Flow-gap-analyst checks for missing components/tokens/breakpoints
- [ ] Flow-gap-analyst section skipped when no DESIGN.md exists
- [ ] Both agents remain read-only (no new tool access)
- [ ] Both sections are advisory (flag, never block)
## Done summary
Added conditional DESIGN.md-aware sections to both agents:

- **quality-auditor.md**: Section 8 (Design System Conformance) checks hard-coded colors, spacing, missing token usage, component drift in frontend files. Advisory only. Output format extended with Design Conformance block.
- **flow-gap-analyst.md**: Section 6 (Design System Alignment) checks for missing components, tokens, breakpoints needed by the feature. Output format extended with Design Gaps block.

Both sections conditional ("skip if no DESIGN.md"). Both agents remain read-only (disallowedTools unchanged). Zero impact on projects without DESIGN.md.
## Evidence
- Commits:
- Tests:
- PRs: