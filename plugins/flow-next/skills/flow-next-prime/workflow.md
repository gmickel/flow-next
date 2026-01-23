# Flow Prime Workflow

Execute these phases in order. Reference [pillars.md](pillars.md) for scoring criteria and [remediation.md](remediation.md) for fix templates.

**Model guidance**: This skill uses sonnet for synthesis and report generation. Scouts run as haiku for speed.

---

## Phase 1: Parallel Assessment

Run all 9 scouts in parallel using the Task tool:

### Agent Readiness Scouts (Pillars 1-5)

```
Task flow-next:tooling-scout    # linters, formatters, pre-commit, type checking
Task flow-next:claude-md-scout  # CLAUDE.md/AGENTS.md quality
Task flow-next:env-scout        # .env.example, docker, devcontainer
Task flow-next:testing-scout    # test framework, coverage, commands
Task flow-next:build-scout      # build system, scripts, CI
Task flow-next:docs-gap-scout   # README, ADRs, architecture docs
```

### Production Readiness Scouts (Pillars 6-8)

```
Task flow-next:observability-scout  # logging, tracing, metrics, health
Task flow-next:security-scout       # branch protection, CODEOWNERS, secrets
Task flow-next:workflow-scout       # CI/CD, templates, automation
```

**Important**: Launch all 9 scouts in parallel for speed (~15-20 seconds total).

Wait for all scouts to complete. Collect findings.

---

## Phase 2: Verification (Optional but Recommended)

After scouts complete, verify key commands actually work.

### Test Verification

If test framework detected by testing-scout, verify tests are runnable using the **appropriate command for the detected framework**.

**Common examples** (adapt to whatever framework is detected):

| Framework | Verification Command |
|-----------|---------------------|
| pytest | `pytest --collect-only` |
| Jest | `npx jest --listTests` |
| Vitest | `npx vitest --run --reporter=dot` |
| Mocha | `npx mocha --dry-run` |
| Go test | `go test ./... -list .` |
| Cargo test | `cargo test --no-run` |
| PHPUnit | `phpunit --list-tests` |

These are examples. For other frameworks, find the equivalent "list tests" or "dry run" command. The goal is to verify tests are discoverable without actually running them.

**For monorepos**: Run verification in each app directory that has tests.

**Adapt to project**: Use the package manager detected (pnpm/npm/yarn/bun). If venv detected for Python, activate it first.

Example:
```bash
# Python with venv
cd apps/api && source .venv/bin/activate && pytest --collect-only 2>&1 | head -20

# JS with pnpm
pnpm test --passWithNoTests 2>&1 | head -10

# Go
go test ./... -list . 2>&1 | head -20
```

Mark TS4 as ✅ only if verification succeeds (tests are discoverable and runnable).

### Build Verification (Quick)

```bash
# Check if build command exists and is valid
pnpm build --help 2>&1 | head -5 || npm run build --help 2>&1 | head -5
```

---

## Phase 3: Score & Synthesize

Read [pillars.md](pillars.md) for pillar definitions and criteria.

### Agent Readiness Score (Pillars 1-5)

For each pillar (1-5):
1. Map scout findings to criteria (pass/fail)
2. Calculate pillar score: `(passed / total) * 100`

Calculate:
- **Agent Readiness Score**: average of Pillars 1-5 scores
- **Maturity Level**: based on thresholds in pillars.md

### Production Readiness Score (Pillars 6-8)

For each pillar (6-8):
1. Map scout findings to criteria (pass/fail)
2. Calculate pillar score: `(passed / total) * 100`

Calculate:
- **Production Readiness Score**: average of Pillars 6-8 scores

### Overall Score

**Overall Score** = average of all 8 pillar scores

### Prioritize Recommendations

Generate prioritized recommendations from **Pillars 1-5 only**:
1. Critical first (CLAUDE.md, .env.example)
2. High impact second (pre-commit hooks, lint commands)
3. Medium last (build scripts, .gitignore)

**Never offer fixes for Pillars 6-8** — these are informational only.

---

## Phase 4: Present Report

```markdown
# Agent Readiness Report

**Repository**: [name]
**Assessed**: [timestamp]

## Scores Summary

| Category | Score | Level |
|----------|-------|-------|
| **Agent Readiness** (Pillars 1-5) | X% | Level N - [Name] |
| Production Readiness (Pillars 6-8) | X% | — |
| **Overall** | X% | — |

## Agent Readiness (Pillars 1-5)

These affect your maturity level and are eligible for fixes.

| Pillar | Score | Status |
|--------|-------|--------|
| Style & Validation | X% (N/6) | ✅ ≥80% / ⚠️ 40-79% / ❌ <40% |
| Build System | X% (N/6) | ✅/⚠️/❌ |
| Testing | X% (N/6) | ✅/⚠️/❌ |
| Documentation | X% (N/6) | ✅/⚠️/❌ |
| Dev Environment | X% (N/6) | ✅/⚠️/❌ |

## Production Readiness (Pillars 6-8)

Informational only. No fixes offered — address independently if desired.

| Pillar | Score | Status |
|--------|-------|--------|
| Observability | X% (N/6) | ✅/⚠️/❌ |
| Security | X% (N/6) | ✅/⚠️/❌ |
| Workflow & Process | X% (N/6) | ✅/⚠️/❌ |

## Detailed Findings

### Pillar 1: Style & Validation (X%)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| SV1: Linter | ✅/❌ | [details] |
| SV2: Formatter | ✅/❌ | [details] |
| ... | ... | ... |

[Repeat for each pillar]

## Top Recommendations (Agent Readiness)

1. **[Category]**: [specific action] — [why it helps agents]
2. **[Category]**: [specific action] — [why it helps agents]
3. **[Category]**: [specific action] — [why it helps agents]

## Production Readiness Notes

[Key observations from Pillars 6-8 that the team should be aware of]
```

**If `--report-only`**: Stop here. Show report and exit.

---

## Phase 5: Interactive Remediation

**If `--fix-all`**: Skip to Phase 6, apply all recommendations from Pillars 1-5.

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
        "label": "Add linter config",
        "description": "[Tool] configuration for code quality checks. Agents can run lint to verify their changes."
      },
      {
        "label": "Add formatter config",
        "description": "[Tool] configuration for consistent code style. Prevents style drift across agent sessions."
      },
      {
        "label": "Add runtime version file",
        "description": "Pin [runtime] version. Ensures consistent environment across machines."
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
        "description": "[Framework] configuration file. Enables test command for agents to verify changes."
      },
      {
        "label": "Add test script",
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

1. **MUST use AskUserQuestion tool** — Never just print questions
2. **Mark recommended items** — Add "(Recommended)" to high-impact options
3. **Mark bonus items** — Add "(Bonus)" to nice-to-have options
4. **Explain agent benefit** — Each description should say WHY it helps agents
5. **Skip empty categories** — Don't ask if no recommendations
6. **Max 4 options per question** — Tool limit, prioritize if more
7. **Never offer Pillar 6-8 items** — Production readiness is informational only

---

## Phase 6: Apply Fixes

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

---

## Phase 7: Summary

After fixes applied:

```markdown
## Changes Applied

### Created
- `CLAUDE.md` — Project conventions for agents
- `.env.example` — Environment variable template

### Modified
- `package.json` — Added lint-staged config

### Skipped (user declined)
- Pre-commit hooks

### Not Offered (production readiness)
- CI/CD, PR templates, observability, security — address independently if desired
```

Offer re-assessment only if changes were made:

```
Run assessment again to see updated score?
```

If yes, run Phase 1-4 again and show:
- New Agent Readiness score and maturity level
- Score changes per pillar
- Remaining recommendations
