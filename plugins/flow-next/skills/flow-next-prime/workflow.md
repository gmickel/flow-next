# Flow Prime Workflow

Execute these phases in order. Reference [pillars.md](pillars.md) for scoring criteria and [remediation.md](remediation.md) for fix templates.

## Phase 1: Parallel Assessment

Run all scouts in parallel using the Task tool (all haiku, fast):

```
Task flow-next:tooling-scout   # linters, formatters, pre-commit, type checking
Task flow-next:claude-md-scout # CLAUDE.md/AGENTS.md quality
Task flow-next:env-scout       # .env.example, docker, devcontainer
Task flow-next:testing-scout   # test framework, coverage, commands
Task flow-next:build-scout     # build system, scripts, CI
Task flow-next:docs-gap-scout  # README, ADRs, architecture docs (existing agent)
```

Wait for all scouts to complete. Collect findings.

## Phase 2: Score & Synthesize

Read [pillars.md](pillars.md) for pillar definitions and criteria.

For each pillar:
1. Map scout findings to criteria (pass/fail)
2. Calculate pillar score: `(passed / total) * 100`

Calculate overall:
- **Overall score**: average of all pillar scores
- **Maturity level**: based on thresholds in pillars.md

Generate prioritized recommendations:
1. High impact, low effort first (e.g., add .env.example)
2. Group by category for user decision

## Phase 3: Present Report

```markdown
# Agent Readiness Report

**Repository**: [name]
**Maturity Level**: [1-5] - [label]
**Overall Score**: [X]%

## Pillar Scores

| Pillar | Score | Status |
|--------|-------|--------|
| Style & Validation | X% | ✅ ≥80% / ⚠️ 40-79% / ❌ <40% |
| Build System | X% | ✅/⚠️/❌ |
| Testing | X% | ✅/⚠️/❌ |
| Documentation | X% | ✅/⚠️/❌ |
| Dev Environment | X% | ✅/⚠️/❌ |
| Code Quality | X% | ✅/⚠️/❌ |

## Top Recommendations

1. **[Category]**: [specific action] - [impact]
2. **[Category]**: [specific action] - [impact]
3. **[Category]**: [specific action] - [impact]

## Detailed Findings

[Per-pillar breakdown from scouts]
```

**If `--report-only`**: Stop here. Show report and exit.

## Phase 4: Interactive Remediation

**If `--fix-all`**: Skip to Phase 5, apply all recommendations.

Otherwise, use **AskUserQuestion** tool to get consent.

Group recommendations by category:

```
Based on the assessment, I can help improve agent readiness.

Which improvements would you like me to apply?
```

Use AskUserQuestion with:
- `multiSelect: true` (user can pick multiple)
- Group options by impact (high/medium/low)
- Include brief description of each fix

Example question structure:
```json
{
  "question": "Which documentation improvements should I apply?",
  "header": "Docs",
  "multiSelect": true,
  "options": [
    {"label": "Create CLAUDE.md", "description": "Project conventions, commands, structure for agents"},
    {"label": "Add .env.example", "description": "Template with 5 detected env vars"},
    {"label": "Create ADR template", "description": "Architecture decision records in docs/adr/"}
  ]
}
```

Ask separate questions for each category with improvements:
- Documentation (if any gaps)
- Tooling (if any gaps)
- Environment (if any gaps)
- Testing (if any gaps)
- CI/Build (if any gaps)

Skip categories with no recommendations.

## Phase 5: Apply Fixes

For each approved fix:
1. Read [remediation.md](remediation.md) for the template
2. Detect project conventions (indent style, quote style, etc.)
3. Adapt template to match conventions
4. Check if target file exists:
   - **New file**: Create it
   - **Existing file**: Show diff and ask before modifying
5. Report what was created/modified

**Non-destructive rules:**
- Never overwrite without explicit consent
- Merge with existing configs when possible
- Use detected project style
- Don't add unused features

## Phase 6: Summary

After fixes applied:

```markdown
## Changes Applied

### Created
- `CLAUDE.md` - Project conventions for agents
- `.env.example` - Environment variable template

### Modified
- `package.json` - Added lint-staged config

### Skipped (user declined)
- Pre-commit hooks
```

Offer re-assessment:

```
Re-run assessment to see updated score? (Recommended to verify improvements)
```

If yes, run Phase 1-3 again and show:
- New maturity level
- Score changes per pillar
- Remaining recommendations
