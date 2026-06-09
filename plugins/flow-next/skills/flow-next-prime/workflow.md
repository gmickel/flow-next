# Flow Prime Workflow

Execute these phases in order. Reference [pillars.md](pillars.md) for scoring criteria and [remediation.md](remediation.md) for fix templates.

**Model guidance**: This skill uses sonnet for synthesis and report generation. Scouts run as sonnet for quality.

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

### Glossary signal (DC8 — deterministic, no scout)

One bash call decides DC8 — run it during synthesis (no scout covers it):

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
GLOSSARY_TERMS=$("$FLOWCTL" glossary list --json 2>/dev/null | jq -r '.total_terms // 0')
```

Gate on `total_terms == 0`, NEVER on `[[ -f GLOSSARY.md ]]` — `flowctl glossary remove` leaves a `# Glossary` H1 husk after the last term is removed (the file is project state, never deleted), so a presence check false-passes on an empty husk. Same invariant as interview's doc-aware autodetect.

- `GLOSSARY_TERMS > 0` → DC8 ✅. Report term coverage in Phase 4. Never rewrite, never re-propose existing terms — staleness/alias pruning belongs to `/flow-next:audit`, not prime.
- `GLOSSARY_TERMS == 0` (file absent or husk) → DC8 ❌. Phase 5.5 offers the bootstrap.

### Prioritize Recommendations

Generate prioritized recommendations from **Pillars 1-5 only** (excluding informational sub-criteria DC7 and DE7):
1. Critical first (CLAUDE.md, .env.example)
2. High impact second (pre-commit hooks, lint commands)
3. Medium last (build scripts, .gitignore)

**Never offer fixes for Pillars 6-8** — these are informational only.
**Never offer fixes for DC7/DE7** — informational sub-criteria; surface as suggestions in Top Recommendations only.

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

### Informational suggestions (not scored)

When DE7 fires negative (no `.clawpatch/` or `flowctl repo-map list --count` returns 0), append this line to Top Recommendations:

> Consider: `/flow-next:map` — builds a semantic feature index for richer scope anchoring (optional).

Detection — `flowctl` is **bundled, not on `PATH`** after install, so use the same `FLOWCTL` prelude pattern as the other skills (canonical Droid+Claude fallback; sync-codex.sh rewrites it to `$HOME/.codex/scripts/flowctl` for the Codex mirror):

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
[[ -d .clawpatch ]] && [ "$("$FLOWCTL" repo-map list --count 2>/dev/null)" -gt 0 ]
```

DE7 is informational — surface as a suggestion only; do NOT include it in Phase 5 remediation prompts.

Glossary (DC8) lines — driven by the Phase 3 glossary signal:

- When `GLOSSARY_TERMS == 0`, append:

  > GLOSSARY.md is absent or a husk — Phase 5.5 offers to seed it from the repo (read-back gated). Under `--report-only`, re-run prime without the flag to seed.

- When `GLOSSARY_TERMS > 0`, report coverage instead:

  > GLOSSARY.md: [N] terms — canonical vocabulary available to interview / plan / audit. No action; pruning belongs to `/flow-next:audit`.

DC8 is informational like DE7, but its remediation path differs: it is handled exclusively by the Phase 5.5 bootstrap (read-back gated), never as a Phase 5 question option.

## Production Readiness Notes

[Key observations from Pillars 6-8 that the team should be aware of]
```

**If `--report-only`**: Stop here. Show report and exit.

---

## Phase 5: Interactive Remediation

**If `--fix-all`**: Skip the questions below and continue at Phase 5.5 (the glossary bootstrap keeps its read-back gate even under `--fix-all`); Phase 6 then applies all recommendations from Pillars 1-5.

**CRITICAL**: You MUST use the `AskUserQuestion` tool for consent. Do NOT just print questions as text. (Call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded. sync-codex.sh rewrites this to a plain-text numbered prompt in the Codex mirror.)

### Using AskUserQuestion correctly

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

1. **MUST use `AskUserQuestion` tool** — Never just print questions as text
2. **Mark recommended items** — Add "(Recommended)" to high-impact options
3. **Mark bonus items** — Add "(Bonus)" to nice-to-have options
4. **Explain agent benefit** — Each description should say WHY it helps agents
5. **Skip empty categories** — Don't ask if no recommendations
6. **Max 4 options per question** — Tool limit, prioritize if more
7. **Never offer Pillar 6-8 items** — Production readiness is informational only
8. **Never offer informational sub-criteria (DC7, DE7)** — Surface as suggestions in Top Recommendations only; no auto-run from Phase 5
9. **Never offer DC8 (glossary) as a Phase 5 option** — Its remediation is the dedicated Phase 5.5 bootstrap with its own read-back; a Phase 5 checkbox would bypass the never-write-terms-unseen gate

---

## Phase 5.5: Glossary Bootstrap (DC8)

Runs only when the Phase 3 glossary signal reported `GLOSSARY_TERMS == 0` (GLOSSARY.md absent or husk). When `GLOSSARY_TERMS > 0`, skip this phase entirely — prime never rewrites a populated glossary and never re-proposes existing terms; staleness/alias pruning belongs to `/flow-next:audit`.

`--fix-all` does NOT bypass the read-back below: term definitions are judgment-bearing canonical vocabulary, not mechanical templates — never write terms unseen. (`--report-only` never reaches this phase; the workflow stops at Phase 4.)

### 5.5.1 Scan for load-bearing vocabulary

Build the candidate pool from what Phase 1 already collected plus targeted reads:

- README.md, docs/, CLAUDE.md / AGENTS.md (claude-md-scout and docs-gap-scout findings already summarize these — reuse them, don't re-read wholesale)
- Top-level module / package / directory names
- Domain nouns recurring across `.flow/specs/*.md` and source files
- Places where the SAME concept goes by two names in the repo (naming drift → `_Avoid_` candidates)

Selection bar: a term earns a slot when an agent could plausibly build around the wrong meaning — project-specific nouns, flows, and distinctions (e.g. two near-synonyms that mean different things in THIS repo). Exclude generic programming vocabulary (server, test, build) and anything without file evidence.

### 5.5.2 Propose terms

Draft ~10-20 candidates (fewer is fine for small repos — never pad). Each proposal carries:

- **Term** — canonical name
- **Definition** — 1-3 sentences, concrete, written against the code (not aspirational)
- **Evidence** — at least one file ref (`path` or `path:line`) where the concept lives; a term with no evidence is dropped, not guessed
- **`_Avoid_` aliases** (optional) — only where naming drift is visible in the repo
- **`_Relates to_`** (optional) — cross-references between proposed terms

### 5.5.3 Read-back (mandatory — never write unseen)

Present the FULL proposal — every term with its definition, evidence, and aliases — then ask via `AskUserQuestion` (sync-codex.sh rewrites this to a plain-text numbered prompt in the Codex mirror):

- **Approve all** — write every proposed term
- **Select subset** — user indicates which terms to keep (follow up for the list)
- **Skip** — write nothing

No write happens before this approval. Decline/skip ⇒ DC8 stays ❌, note it in the Phase 7 summary, move on — never re-ask in the same run.

### 5.5.4 Write accepted terms

One `flowctl glossary add` per accepted term — stdin definition so multi-sentence text round-trips cleanly (same call shape as interview's doc-aware write). `glossary add` creates `GLOSSARY.md` at the repo root when no ancestor file exists, and upserts on re-runs:

```bash
"$FLOWCTL" glossary add "<term>" --definition-file - --json <<'EOF'
<definition — 1-3 sentences>
EOF
# optional flags when proposed: --avoid "alt1,alt2" --relates-to "x,y"
```

Verify after the last write:

```bash
"$FLOWCTL" glossary list --json | jq -r '.total_terms'   # must equal the accepted count
```

Record the outcome for Phase 7: seeded N terms / user declined / count mismatch (report it, don't retry-loop).

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
- `GLOSSARY.md` — Seeded with [N] terms (Phase 5.5 bootstrap)

### Modified
- `package.json` — Added lint-staged config

### Skipped (user declined)
- Pre-commit hooks
- Glossary bootstrap (declined at read-back)

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
