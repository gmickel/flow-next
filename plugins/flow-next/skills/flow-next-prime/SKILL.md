---
name: flow-next-prime
description: Comprehensive codebase assessment for agent and production readiness. Classifies the project (lifecycle, topology, size, stack, shape), scans 8 pillars, verifies commands actually run, checks GitHub settings. Leads with a verdict + ranked next-actions; fixes agent readiness only. Triggers on /flow-next:prime.
user-invocable: false
---

# Flow Prime

Comprehensive codebase assessment inspired by [Factory.ai's Agent Readiness framework](https://factory.ai/news/agent-readiness).

**Role**: readiness assessor, improvement proposer
**Goal**: full visibility into codebase health, targeted fixes for agent readiness

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step of this skill.

## Two-Tier Assessment

| Category | Pillars | What Happens |
|----------|---------|--------------|
| **Agent Readiness** | 1-5 | Scored, maturity level calculated, fixes offered |
| **Production Readiness** | 6-8 | Reported for awareness, no fixes offered |

This gives you **full visibility** while keeping remediation focused on what actually helps agents work.

**Criteria counts live in [pillars.md](pillars.md), never here.** pillars.md is the single census source (the legacy scored criteria feeding the maturity level, the informational rows, and the new agent-readiness tier groups AO/DR/TO/HP). Do not restate a count in this file - a hardcoded number drifts the moment a criterion is added. The classification, operability ladder, per-shape playbooks, per-stack matrix, and harness check-set live in the four reference files: [classification.md](classification.md), [playbooks.md](playbooks.md), [stacks.md](stacks.md), [harness.md](harness.md).

## Why This Matters

Existence checks lie. A repo can carry a CLAUDE.md, a hook file, and a `lint` script yet be un-agentic in practice - the file is an empty template, the build is broken, imports don't resolve, or it is really one of 99 sibling repos. Prime judges **substance**, not existence, and names the single highest-leverage next action.

Agents waste cycles when:
- **No closed verify loop** → can't confirm a change works without a full CI round-trip; the feedback gate belongs at the RIGHT layer (edit-time/commit format+lint, tests via the verify command + acceptance requirements + CI required check - never a test-running pre-commit hook agents `--no-verify` around or stall on)
- **Undocumented env vars** → guesses, fails, guesses again
- **No agent instruction file (or a generic/stale one)** → doesn't know project conventions, the operability tier, or which files are off-limits
- **The app can't be built or driven** → can't verify changes work; a legacy stack with no headless build has no feedback loop at all

These are **environment problems**, not agent problems. Prime grades them as layered gates and helps fix the ones that help agents work.

## Input

Full request: $ARGUMENTS

Accepts:
- No arguments (scans current repo)
- `--report-only` or `report only` (skip remediation, just show report)
- `--fix-all` or `fix all` (apply all agent readiness fixes without asking)
- `--classify-only` or `classify only` (print the Phase 0.5 classification block and EXIT - the cheap portfolio-triage sweep over many repos; see classification.md)
- A path to a different repo root (first non-flag argument)

Examples:
- `/flow-next:prime`
- `/flow-next:prime --report-only`
- `/flow-next:prime --classify-only ~/other-project`
- `/flow-next:prime ~/other-project`

**Resolve `ROOT` from `$ARGUMENTS`** (the first non-flag token; default `.`). If `ROOT` is not the
cwd, resolve it first (`ROOT=$(cd "$ROOT" && pwd)`), then it MUST thread through everything: `cd "$ROOT"` before the `.flow/meta.json` pre-check, the
Phase 0.5 classification probes (the `flowctl prime classify` emitter takes `ROOT` as its positional
argument, e.g. `flowctl prime classify --json "$ROOT"`), and the Phase 2 verification commands; and
every scout dispatch prompt in Phase 1 starts "Assess the repo at `ROOT`" (scouts scan cwd by default
- without this they'd scan the wrong repo and the report would be confidently wrong end-to-end). If
threading `ROOT` isn't feasible, error rather than silently scan cwd.

## Route Before Reading References

Parse the mode before loading any reference:

- **`--classify-only`:** read [classification.md](classification.md) directly,
  run its emitter + judgment-layer contract, print its fixed classification block,
  and EXIT. Do **not** read `workflow.md`, `pillars.md`, `playbooks.md`, or
  `remediation.md`; never ask, dispatch scouts, verify, report, or remediate.
- **All other modes:** read [workflow.md](workflow.md) and execute it. The
  workflow loads classification, pillars, playbooks, stacks, harness, and
  remediation guidance only at their consuming phases. `--report-only` stops
  after the report and must never load remediation templates.

This dispatch is fail-open for an unknown/malformed mode: use the full workflow,
never silently skip assessment or safety instructions.

## Workflow

The mode router above selects the entry reference. Do not pre-read references
for branches that will not execute.

## Guardrails

### General
- Never modify code files (only config, docs, scripts)
- Never commit changes (leave for user to review)
- Never delete files
- Respect .gitignore patterns

### User Consent
- **MUST use `AskUserQuestion` tool** for consent (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded). Never just print questions as text.
- Always ask before modifying existing files — **except** under `--fix-all`, which waives the prompt for **append/merge** edits (adding a `.gitignore` line, augmenting an agent file, appending a hook) INCLUDING their required devDependencies for the Critical/High/Medium tiers. `--fix-all` still does NOT: overwrite/replace existing file content unseen, touch the Bonus tier (devcontainer, CI workflow — those stay explicit-request-only), or bypass the glossary read-back gate. A destructive overwrite always needs consent even under `--fix-all`.
- Don't add dependencies without consent (a Critical/High/Medium fix's own devDeps are covered by that fix's consent, incl. `--fix-all`; never add unrelated deps)
- **Glossary terms are never written unseen** — the Phase 5.5 bootstrap shows the full proposal (term + definition + file-ref evidence) at read-back before any `flowctl glossary add`; `--fix-all` does not bypass this gate, and a populated glossary (`total_terms > 0`) is never rewritten

### `--fix-all` boundaries

`--fix-all` auto-applies ONLY **in-`ROOT`, non-structural, non-harness** fixes at the Critical/High/Medium tier - the in-root Pillars 1-5 fixes PLUS scored-group agent-file content whose catalog row is marked `--fix-all`-eligible in its consent column (the ranked catalog carries the tier AND consent columns and **is authoritative** on which scored-group items qualify - see [playbooks.md](playbooks.md)). It NEVER waives consent for:
- **Anything outside the repo `ROOT`** - the home-base / constellation kit (parent instruction file, `repos.yaml`, run-everything scripts) is always explicit-consent-only.
- **Any harness settings/hook file** - deny/ask rule scaffolds, hook wiring, MCP config. A scaffolded hook is exercised in the same pass (never a stub); the offer itself still needs explicit consent.
- **All structural / playbook artifacts** - a generated map, nested per-package instruction files, the home base, the greenfield bootstrap plan. Structural = restructures the repo → explicit consent regardless of tier.
- **On greenfield**, `--fix-all` applies ONLY to exercised hygiene files (`.gitignore`, lockfile, `.env.example`, `.editorconfig`) - never structural or generated artifacts, and never a bulk-generated instruction file (measured harm).

### Scope Control
- **Never create LICENSE files** — license choice requires explicit user decision
- **Never offer Pillar 6-8 fixes** — production readiness is informational only
- Focus fixes on what helps agents work (not team governance)
