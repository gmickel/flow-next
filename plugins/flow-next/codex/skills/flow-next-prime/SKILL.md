---
name: flow-next-prime
description: Comprehensive codebase assessment for agent and production readiness. Classifies the project (lifecycle, topology, size, stack, shape), scans 8 pillars, verifies commands actually run, checks GitHub settings. Leads with a verdict + ranked next-actions; fixes agent readiness only. Triggers on /flow-next:prime.
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
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json"
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

If the block printed a `FLOW_SETUP_ASK` line, before proceeding ask the user with plain-text numbered prompt (local setup differs from the plugin; refresh now?), offering exactly the options **Refresh now**, **Remind me next version**, **Skip this run**, then continue the skill whichever is chosen:
- **Refresh now**: pause and have the user run `/flow-next:setup` in this session (do not run setup yourself), then continue once it finishes.
- **Remind me next version**: record the acknowledgement so this version is not re-asked (only a later plugin version re-arms it), then continue. Run this self-contained write (fail-open: on any error, continue anyway):
 ```bash
 PJ="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json"
 PV=$(jq -r '.version' "$PJ" 2>/dev/null)
 [[ -n "$PV" && "$PV" != "null" ]] && rm -f .flow/meta.json.tmp && jq --arg v "$PV" '.version_ack = $v' .flow/meta.json > .flow/meta.json.tmp && mv .flow/meta.json.tmp .flow/meta.json
 ```
- **Skip this run**: continue without writing anything; the next invocation asks again.

Any other output (the one-line differs notice, or nothing) is non-blocking: continue.

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
- `--classify-only` or `classify only` (print the Phase 0.5 classification block and EXIT - the cheap portfolio-triage sweep over many repos; see Phase 0.5 in workflow.md)
- A path to a different repo root (first non-flag argument)

Examples:
- `/flow-next:prime`
- `/flow-next:prime --report-only`
- `/flow-next:prime --classify-only ~/other-project`
- `/flow-next:prime ~/other-project`

**Resolve `ROOT` from `$ARGUMENTS`** (the first non-flag token; default `.`). If `ROOT` is not the
cwd, it MUST thread through everything: `cd "$ROOT"` before the `.flow/meta.json` pre-check, the
Phase 0.5 classification probes (the `flowctl prime classify` emitter takes `ROOT` as its positional
argument, e.g. `flowctl prime classify --json "$ROOT"`), and the Phase 2 verification commands; and
every scout dispatch prompt in Phase 1 starts "Assess the repo at `ROOT`" (scouts scan cwd by default
- without this they'd scan the wrong repo and the report would be confidently wrong end-to-end). If
threading `ROOT` isn't feasible, error rather than silently scan cwd.

`--classify-only` is the fast path: it runs Phase 0.5 (emitter + the skill's judgment layer), prints
the classification block, and exits - it NEVER asks (Phase 0.6 is skipped), NEVER dispatches scouts,
and NEVER remediates. It must stay cheap (<~10s even on a multi-M-LOC repo).

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
0.5. **Classify** - host-inline five-axis classification (lifecycle / topology / size / stack / shape) via the `flowctl prime classify` emitter + the skill's judgment layer, per [classification.md](classification.md). Parameterizes everything downstream (scout dispatch, N/A denominators, report shape, playbook selection). `--classify-only` prints this block and exits.
0.6. **Targeted clarification** - the bounded R15 ask protocol: at most one question call for low-confidence or uninferable facts that change a playbook or verdict; confirmed answers offered for durable recording in the agent file. Suppressed under `--classify-only` / `--report-only` / autonomous.
1. **Parallel Assessment** - 9 scouts run in parallel (7 haiku fast scanners; agents-md-scout + docs-gap-scout on sonnet for judgment), each consuming the Phase 0.5 classification (~15-20 seconds)
2. **Verification** — Verify test commands actually work
3. **Score, Synthesize & Assemble the Verdict** - Calculate pillar scores + maturity level (includes the deterministic DC8 glossary signal - `flowctl glossary list --json`, gated on `total_terms == 0`, never file presence); evaluate the host-inline AO/DR/TO/HP groups as level-excluded pass-count lines; derive the DR-core QA-readiness line + feedback-latency + gh-CLI host lines; assemble the verdict headline inputs
4. **Present Report** — Full report with all 8 pillars
5. **Interactive Remediation** — `plain-text numbered prompt` for agent readiness fixes only
5.5. **Glossary Bootstrap** — when the glossary has zero terms (absent or husk), propose evidence-backed terms from the repo and seed `GLOSSARY.md` via `flowctl glossary add` after read-back approval; a populated glossary gets a coverage line, never a rewrite
6. **Apply Fixes** — Create/modify files based on selections
7. **Summary** — Show what was changed

## Maturity Levels (Agent Readiness)

**The maturity level is secondary metadata, NOT the headline.** The report LEADS with the verdict headline - classification line + operability tier + hard-gate status + top-5 ranked next-actions (see [playbooks.md](playbooks.md)). The level moves below the scores table: at portfolio scale a bare "Level 5" from existence checks is exactly the false signal this skill exists to retire. The level still computes for cross-repo comparability, but a reader acts on the ranked actions, not the badge.

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
- Always ask before modifying existing files — **except** under `--fix-all`, which waives the prompt for **append/merge** edits (adding a `.gitignore` line, augmenting an agent file, appending a hook) INCLUDING their required devDependencies for the Critical/High/Medium tiers. `--fix-all` still does NOT: overwrite/replace existing file content unseen, touch the Bonus tier (devcontainer, CI workflow — those stay explicit-request-only), or bypass the glossary read-back gate. A destructive overwrite always needs consent even under `--fix-all`.
- Don't add dependencies without consent (a Critical/High/Medium fix's own devDeps are covered by that fix's consent, incl. `--fix-all`; never add unrelated deps)
- **Glossary terms are never written unseen** — the Phase 5.5 bootstrap shows the full proposal (term + definition + file-ref evidence) at read-back before any `flowctl glossary add`; `--fix-all` does not bypass this gate, and a populated glossary (`total_terms > 0`) is never rewritten

### `--fix-all` boundaries (resolutions 5/6)

`--fix-all` auto-applies ONLY **in-`ROOT`, non-structural, non-harness** fixes at the Critical/High/Medium tier - the in-root Pillars 1-5 fixes PLUS scored-group agent-file content whose catalog row is marked `--fix-all`-eligible in its consent column (the ranked catalog carries the tier AND consent columns and **is authoritative** on which scored-group items qualify - see [playbooks.md](playbooks.md)). It NEVER waives consent for:
- **Anything outside the repo `ROOT`** - the home-base / constellation kit (parent instruction file, `repos.yaml`, run-everything scripts) is always explicit-consent-only.
- **Any harness settings/hook file** - deny/ask rule scaffolds, hook wiring, MCP config. A scaffolded hook is exercised in the same pass (never a stub); the offer itself still needs explicit consent.
- **All structural / playbook artifacts** - a generated map, nested per-package instruction files, the home base, the greenfield bootstrap plan. Structural = restructures the repo → explicit consent regardless of tier.
- **On greenfield**, `--fix-all` applies ONLY to exercised hygiene files (`.gitignore`, lockfile, `.env.example`, `.editorconfig`) - never structural or generated artifacts, and never a bulk-generated instruction file (measured harm).

**Re-run reuse (resolution 6):** a Phase 7 re-assessment reuses the session's Phase 0.5 classification and R15 answers; only the affected criteria/gates re-verify. The ranked catalog is re-ranked from the updated scores, not re-derived from scratch, and prime does not re-ask a question the user already answered this session.

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
