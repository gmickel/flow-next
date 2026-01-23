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

**Important**: Only Pillars 1-5 affect the maturity score. Pillar 6 (Team Governance) is informational only.

For each pillar (1-5):
1. Map scout findings to criteria (pass/fail)
2. Calculate pillar score: `(passed / total) * 100`

For Pillar 6:
- Report findings for awareness
- Do NOT include in overall score
- Do NOT offer remediation

Calculate overall:
- **Overall score**: average of Pillars 1-5 only
- **Maturity level**: based on thresholds in pillars.md

Generate prioritized recommendations (from Pillars 1-5 only):
1. Critical first (CLAUDE.md, .env.example)
2. High impact second (pre-commit hooks, lint commands)
3. Medium last (build scripts, .gitignore)
4. Never offer team governance fixes (Pillar 6 items)

## Phase 3: Present Report

```markdown
# Agent Readiness Report

**Repository**: [name]
**Maturity Level**: [1-5] - [label]
**Overall Score**: [X]% (Pillars 1-5)

## Pillar Scores

| Pillar | Score | Status |
|--------|-------|--------|
| Style & Validation | X% | ✅ ≥80% / ⚠️ 40-79% / ❌ <40% |
| Build System | X% | ✅/⚠️/❌ |
| Testing | X% | ✅/⚠️/❌ |
| Documentation | X% | ✅/⚠️/❌ |
| Dev Environment | X% | ✅/⚠️/❌ |

## Team Governance (Informational)

| Item | Status |
|------|--------|
| CONTRIBUTING.md | ✅/❌ |
| PR Template | ✅/❌ |
| License | ✅/❌ |
...

*Note: Team governance items don't affect agent maturity. Address independently if desired.*

## Top Recommendations

1. **[Category]**: [specific action] - [why it helps agents]
2. **[Category]**: [specific action] - [why it helps agents]
3. **[Category]**: [specific action] - [why it helps agents]

## Detailed Findings

[Per-pillar breakdown from scouts]
```

**If `--report-only`**: Stop here. Show report and exit.

## Phase 4: Interactive Remediation

**If `--fix-all`**: Skip to Phase 5, apply all recommendations from Pillars 1-5.

**CRITICAL**: You MUST use the `AskUserQuestion` tool for consent. Do NOT just print questions as text.

### Using AskUserQuestion Correctly

The tool provides an interactive UI. Each question should:
- Have a clear header (max 12 chars)
- Explain what each option does and WHY it helps agents
- Use `multiSelect: true` so users can pick multiple items
- Include impact description for each option

### Question Structure

Ask ONE question per category that has recommendations. Skip categories with no gaps.

**Question 1: Documentation (if gaps exist)**

```json
{
  "questions": [{
    "question": "Which documentation improvements should I create? These help agents understand your project without guessing.",
    "header": "Docs",
    "multiSelect": true,
    "options": [
      {
        "label": "Create CLAUDE.md (Recommended)",
        "description": "Agent instruction file with commands, conventions, and project structure. Critical for agents to work effectively."
      },
      {
        "label": "Create .env.example",
        "description": "Template with [N] detected env vars. Prevents agents from guessing required configuration."
      }
    ]
  }]
}
```

**Question 2: Tooling (if gaps exist)**

```json
{
  "questions": [{
    "question": "Which tooling improvements should I add? These give agents instant feedback instead of waiting for CI.",
    "header": "Tooling",
    "multiSelect": true,
    "options": [
      {
        "label": "Add pre-commit hooks (Recommended)",
        "description": "Husky + lint-staged for instant lint/format feedback. Catches errors in 5 seconds instead of 10 minutes."
      },
      {
        "label": "Add ESLint config",
        "description": "Linter configuration for code quality checks. Agents can run 'npm run lint' to verify their changes."
      },
      {
        "label": "Add Prettier config",
        "description": "Formatter configuration for consistent code style. Prevents style drift across agent sessions."
      },
      {
        "label": "Add .nvmrc",
        "description": "Pin Node.js version to [detected version]. Ensures consistent runtime across environments."
      }
    ]
  }]
}
```

**Question 3: Testing (if gaps exist)**

```json
{
  "questions": [{
    "question": "Which testing improvements should I add? These let agents verify their work.",
    "header": "Testing",
    "multiSelect": true,
    "options": [
      {
        "label": "Add test config (Recommended)",
        "description": "[Framework] configuration file. Enables 'npm test' command for agents to verify changes."
      },
      {
        "label": "Add test script to package.json",
        "description": "Adds 'test' command that agents can discover and run."
      }
    ]
  }]
}
```

**Question 4: Environment (if gaps exist)**

```json
{
  "questions": [{
    "question": "Which environment improvements should I add?",
    "header": "Environment",
    "multiSelect": true,
    "options": [
      {
        "label": "Add .gitignore entries (Recommended)",
        "description": "Ignore .env, build outputs, node_modules. Prevents accidental commits of sensitive data."
      },
      {
        "label": "Create devcontainer (Bonus)",
        "description": "VS Code devcontainer config for reproducible environment. Nice-to-have, not essential for agents."
      }
    ]
  }]
}
```

### Rules for Questions

1. **MUST use AskUserQuestion tool** - Never just print questions
2. **Mark recommended items** - Add "(Recommended)" to high-impact options
3. **Mark bonus items** - Add "(Bonus)" to nice-to-have options
4. **Explain agent benefit** - Each description should say WHY it helps agents
5. **Skip empty categories** - Don't ask if no recommendations
6. **Max 4 options per question** - Tool limit, prioritize if more
7. **Never offer Pillar 6 items** - Team governance is informational only

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

### Not Offered (team governance)
- CONTRIBUTING.md, PR templates, etc. (address independently if desired)
```

Offer re-assessment only if changes were made:

```
Run assessment again to see updated score?
```

If yes, run Phase 1-3 again and show:
- New maturity level
- Score changes per pillar
- Remaining recommendations
