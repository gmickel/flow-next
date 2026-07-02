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

Non-blocking, same pattern as `/flow-next:plan` — one-line nag when the local setup lags the plugin:

```bash
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
 echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})." >&2
fi
```

Continue regardless (never blocks; silent when setup was never run or versions match).

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
- Path to different repo root

Examples:
- `/flow-next:prime`
- `/flow-next:prime --report-only`
- `/flow-next:prime ~/other-project`

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
1. **Parallel Assessment** — 9 scouts run in parallel (7 haiku fast scanners; agents-md-scout + docs-gap-scout on sonnet for judgment) (~15-20 seconds)
2. **Verification** — Verify test commands actually work
3. **Score & Synthesize** — Calculate scores, determine maturity level (includes the deterministic DC8 glossary signal — `flowctl glossary list --json`, gated on `total_terms == 0`, never file presence)
4. **Present Report** — Full report with all 8 pillars
5. **Interactive Remediation** — `plain-text numbered prompt` for agent readiness fixes only
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

## What Gets Fixed vs Reported

| Pillars | Category | Remediation |
|---------|----------|-------------|
| 1-5 | Agent Readiness | ✅ Fixes offered via plain-text numbered prompt |
| 6-8 | Production Readiness | ❌ Reported only, address independently |

## Guardrails

### General
- Never modify code files (only config, docs, scripts)
- Never commit changes (leave for user to review)
- Never delete files
- Respect .gitignore patterns

### User Consent
- **MUST ask via the plain-text numbered prompt described below** for consent.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.
- Always ask before modifying existing files
- Don't add dependencies without consent
- **Glossary terms are never written unseen** — the Phase 5.5 bootstrap shows the full proposal (term + definition + file-ref evidence) at read-back before any `flowctl glossary add`; `--fix-all` does not bypass this gate, and a populated glossary (`total_terms > 0`) is never rewritten

### Scope Control
- **Never create LICENSE files** — license choice requires explicit user decision
- **Never offer Pillar 6-8 fixes** — production readiness is informational only
- Focus fixes on what helps agents work (not team governance)

## Scouts

### Agent Readiness (haiku fast scanners; agents-md-scout + docs-gap-scout on sonnet)
- `tooling-scout` — linters, formatters, pre-commit, type checking
- `agents-md-scout` — CLAUDE.md/AGENTS.md analysis (sonnet — judgment-heavy)
- `env-scout` — environment setup
- `testing-scout` — test infrastructure
- `build-scout` — build system
- `docs-gap-scout` — README, ADRs, architecture (sonnet — judgment-heavy)

### Production Readiness (haiku, fast)
- `observability-scout` — logging, tracing, metrics, health
- `security-scout` — GitHub settings, CODEOWNERS, secrets
- `workflow-scout` — CI/CD, templates, automation

All 9 scouts run in parallel for speed.
