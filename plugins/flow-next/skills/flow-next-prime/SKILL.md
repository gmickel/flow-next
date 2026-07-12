---
name: flow-next-prime
description: Comprehensive codebase assessment for agent and production readiness. Scans 8 pillars (48 criteria), verifies commands work, checks GitHub settings. Reports everything, fixes agent readiness only. Triggers on /flow-next:prime.
user-invocable: false
---

# Flow Prime

Comprehensive codebase assessment inspired by [Factory.ai's Agent Readiness framework](https://factory.ai/news/agent-readiness).

**Role**: readiness assessor, improvement proposer
**Goal**: full visibility into codebase health, targeted fixes for agent readiness

## Two-Tier Assessment

## Pre-check: Local setup version

Compare `.flow/meta.json` `setup_version` to the plugin version; on mismatch, escalate once per plugin version. Fail-open throughout: a missing `jq`, `.flow/meta.json`, or plugin manifest silently continues.

```bash
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
VERSION_ACK=$(jq -r '.version_ack // empty' .flow/meta.json 2>/dev/null)
if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
  if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
        || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* \
        || "$VERSION_ACK" == "$PLUGIN_VER" ]]; then
    echo "Local setup v${SETUP_VER} differs from plugin v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts." >&2
  else
    echo "FLOW_SETUP_ASK ${SETUP_VER} ${PLUGIN_VER}"
  fi
fi
```

If the block printed a `FLOW_SETUP_ASK` line, before proceeding ask the user with AskUserQuestion (local setup differs from the plugin; refresh now?), offering exactly the options **Refresh now**, **Remind me next version**, **Skip this run**, then continue the skill whichever is chosen:
- **Refresh now**: pause and have the user run `/flow-next:setup` in this session (do not run setup yourself), then continue once it finishes.
- **Remind me next version**: record the acknowledgement so this version is not re-asked (only a later plugin version re-arms it), then continue. Run this self-contained write (fail-open: on any error, continue anyway):
  ```bash
  PJ="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
  PV=$(jq -r '.version' "$PJ" 2>/dev/null)
  [[ -n "$PV" && "$PV" != "null" ]] && rm -f .flow/meta.json.tmp && jq --arg v "$PV" '.version_ack = $v' .flow/meta.json > .flow/meta.json.tmp && mv .flow/meta.json.tmp .flow/meta.json
  ```
- **Skip this run**: continue without writing anything; the next invocation asks again.

Any other output (the one-line differs notice, or nothing) is non-blocking: continue.

| Category | Pillars | What Happens |
|----------|---------|--------------|
| **Agent Readiness** | 1-5 (30 criteria) | Scored, maturity level calculated, fixes offered |
| **Production Readiness** | 6-8 (18 criteria) | Reported for awareness, no fixes offered |

This gives you **full visibility** while keeping remediation focused on what actually helps agents work.

## Why This Matters

Agents waste cycles when:
- No pre-commit hooks → waits 10min for CI instead of 5sec local feedback
- Undocumented env vars → guesses, fails, guesses again
- No CLAUDE.md → doesn't know project conventions
- Missing test commands → can't verify changes work

These are **environment problems**, not agent problems. Prime helps fix them.

## Input

Full request: $ARGUMENTS

Accepts:
- No arguments (scans current repo)
- `--report-only` or `report only` (skip remediation, just show report)
- `--fix-all` or `fix all` (apply all agent readiness fixes without asking)
- A path to a different repo root (first non-flag argument)

Examples:
- `/flow-next:prime`
- `/flow-next:prime --report-only`
- `/flow-next:prime ~/other-project`

**Resolve `ROOT` from `$ARGUMENTS`** (the first non-flag token; default `.`). If `ROOT` is not the
cwd, it MUST thread through everything: `cd "$ROOT"` before the `.flow/meta.json` pre-check and the
Phase 2 verification commands, and every scout dispatch prompt in Phase 1 starts "Assess the repo at
`ROOT`" (scouts scan cwd by default — without this they'd scan the wrong repo and the report would be
confidently wrong end-to-end). If threading `ROOT` isn't feasible, error rather than silently scan cwd.

## The Eight Pillars

### Agent Readiness (Pillars 1-5) — Fixes Offered

| Pillar | What It Checks |
|--------|----------------|
| **1. Style & Validation** | Linters, formatters, type checking, pre-commit hooks |
| **2. Build System** | Build tools, commands, lock files, monorepo tooling |
| **3. Testing** | Test framework, commands, coverage, verification |
| **4. Documentation** | README, CLAUDE.md, setup docs, architecture |
| **5. Dev Environment** | .env.example, Docker, devcontainer, runtime version |

### Production Readiness (Pillars 6-8) — Report Only

| Pillar | What It Checks |
|--------|----------------|
| **6. Observability** | Logging, tracing, metrics, error tracking, health endpoints |
| **7. Security** | Branch protection, secret scanning, CODEOWNERS, Dependabot |
| **8. Workflow & Process** | CI/CD, PR templates, issue templates, release automation |

## Workflow

Read [workflow.md](workflow.md) and execute each phase in order.

**Key phases:**
1. **Parallel Assessment** — 9 scouts run in parallel (7 haiku fast scanners; claude-md-scout + docs-gap-scout on sonnet for judgment) (~15-20 seconds)
2. **Verification** — Verify test commands actually work
3. **Score & Synthesize** — Calculate scores, determine maturity level (includes the deterministic DC8 glossary signal — `flowctl glossary list --json`, gated on `total_terms == 0`, never file presence)
4. **Present Report** — Full report with all 8 pillars
5. **Interactive Remediation** — `AskUserQuestion` for agent readiness fixes only
5.5. **Glossary Bootstrap** — when the glossary has zero terms (absent or husk), propose evidence-backed terms from the repo and seed `GLOSSARY.md` via `flowctl glossary add` after read-back approval; a populated glossary gets a coverage line, never a rewrite
6. **Apply Fixes** — Create/modify files based on selections
7. **Summary** — Show what was changed

## Maturity Levels (Agent Readiness)

| Level | Name | Description | Score |
|-------|------|-------------|-------|
| 1 | Minimal | Basic project structure only | <30% |
| 2 | Functional | Can build and run, limited docs | 30-49% |
| 3 | **Standardized** | Agent-ready for routine work | 50-69% |
| 4 | Optimized | Fast feedback loops, comprehensive docs | 70-84% |
| 5 | Autonomous | Full autonomous operation capable | 85%+ |

**Level 3 is the target** for most teams. Don't over-engineer.

> **The score band above is necessary but NOT sufficient.** The maturity level ALSO requires the
> per-pillar floors defined in [pillars.md](pillars.md) (Level 3 needs every pillar ≥40%, L4 ≥60%,
> L5 ≥80%). pillars.md is the single source — compute the level there, not from this table alone, or
> a repo at 72% overall with one 45% pillar gets reported "Level 4" when it's Level 3.

## What Gets Fixed vs Reported

| Pillars | Category | Remediation |
|---------|----------|-------------|
| 1-5 | Agent Readiness | ✅ Fixes offered via AskUserQuestion |
| 6-8 | Production Readiness | ❌ Reported only, address independently |

## Guardrails

### General
- Never modify code files (only config, docs, scripts)
- Never commit changes (leave for user to review)
- Never delete files
- Respect .gitignore patterns

### User Consent
- **MUST use `AskUserQuestion` tool** for consent (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded). Never just print questions as text. (sync-codex.sh rewrites this to a plain-text numbered prompt in the Codex mirror.)
- Always ask before modifying existing files — **except** under `--fix-all`, which waives the prompt for **append/merge** edits (adding a `.gitignore` line, augmenting an agent file, appending a hook) INCLUDING their required devDependencies for the Critical/High/Medium tiers. `--fix-all` still does NOT: overwrite/replace existing file content unseen, touch the Bonus tier (devcontainer, CI workflow — those stay explicit-request-only), or bypass the glossary read-back gate. A destructive overwrite always needs consent even under `--fix-all`.
- Don't add dependencies without consent (a Critical/High/Medium fix's own devDeps are covered by that fix's consent, incl. `--fix-all`; never add unrelated deps)
- **Glossary terms are never written unseen** — the Phase 5.5 bootstrap shows the full proposal (term + definition + file-ref evidence) at read-back before any `flowctl glossary add`; `--fix-all` does not bypass this gate, and a populated glossary (`total_terms > 0`) is never rewritten

### Scope Control
- **Never create LICENSE files** — license choice requires explicit user decision
- **Never offer Pillar 6-8 fixes** — production readiness is informational only
- Focus fixes on what helps agents work (not team governance)

## Scouts

### Agent Readiness (haiku fast scanners; claude-md-scout + docs-gap-scout on sonnet)
- `tooling-scout` — linters, formatters, pre-commit, type checking
- `claude-md-scout` — CLAUDE.md/AGENTS.md analysis (sonnet — judgment-heavy)
- `env-scout` — environment setup
- `testing-scout` — test infrastructure
- `build-scout` — build system
- `docs-gap-scout` — README, ADRs, architecture (sonnet — judgment-heavy)

### Production Readiness (haiku, fast)
- `observability-scout` — logging, tracing, metrics, health
- `security-scout` — GitHub settings, CODEOWNERS, secrets
- `workflow-scout` — CI/CD, templates, automation

All 9 scouts run in parallel for speed.
