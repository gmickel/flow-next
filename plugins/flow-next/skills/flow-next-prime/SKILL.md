---
name: flow-next-prime
description: Analyze codebase for agent readiness and propose non-destructive improvements. Scans tooling, docs, environment, testing, and build setup. Works for greenfield and brownfield projects. Triggers on /flow-next:prime.
---

# Flow Prime

Assess and improve your codebase's readiness for agentic development. Inspired by Factory.ai's Agent Readiness framework.

**Role**: readiness assessor, improvement proposer
**Goal**: identify gaps that slow agents down, offer fixes with user consent

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
- `--fix-all` or `fix all` (apply all recommendations without asking)
- Path to different repo root

Examples:
- `/flow-next:prime`
- `/flow-next:prime --report-only`
- `/flow-next:prime ~/other-project`

## Workflow

Read [workflow.md](workflow.md) and execute each phase in order.

## Maturity Levels

| Level | Name | Description |
|-------|------|-------------|
| 1 | Minimal | Basic project structure only |
| 2 | Functional | Can build and run, limited docs |
| 3 | Standardized | Agent-ready for routine work (target) |
| 4 | Optimized | Fast feedback loops, comprehensive docs |
| 5 | Autonomous | Full autonomous operation capable |

**Level 3 is the target** for most teams. Don't over-engineer.

## Scope: Agent Readiness Only

Focus on what helps **agents work effectively**:
- Fast local feedback (pre-commit, lint, format)
- Clear commands (build, test, dev)
- Documentation (CLAUDE.md with conventions)
- Environment (.env.example with required vars)

**NOT in scope** (team governance):
- CONTRIBUTING.md, PR templates, issue templates
- CODEOWNERS, branch protection
- LICENSE (legal decision, not agent readiness)

Pillar 6 (Team Governance) is **informational only** — reported but not scored, no remediation offered.

## Guardrails

- Never modify code files (only config, docs, scripts)
- Never commit changes (leave for user to review)
- Never delete files
- **MUST use AskUserQuestion tool** for consent — never just print questions as text
- Always ask before modifying existing files
- Respect .gitignore patterns
- Don't add dependencies without consent
- **Never create LICENSE files** — license choice requires explicit user decision
- **Never offer team governance fixes** — CONTRIBUTING, PR templates, etc.
