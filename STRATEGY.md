---
name: flow-next
last_updated: 2026-05-16
generator: flow-next-strategy
---

# flow-next Strategy

## Target problem

AI agent workflows drift, lose context, and produce uneven quality at scale. Existing task trackers (Jira, Linear) optimize for human cadence — 2-3 week implementations with daily standups, mid-flight refinement, and design reviews carrying the weight. Agentic engineering compresses implementation to hours, not weeks; the touchpoints that pre-agentic Agile relied on collapse, and the spec has to carry the full weight upstream. Without structured handovers between idea and merge, agents drift mid-task, reviewers face 10K-line diffs with no focus signal, and quality is uneven across runs.

## Our approach

Spec-driven development with re-anchoring, cross-model review, and zero external dependencies. Six named handover objects between idea and merge — each reviewable on its own, cross-model-verified, and frozen at handover. **Specs are single durable documents that evolve through layers** — `.flow/specs/<id>.md` is the source of truth for goal, architecture, R-IDs, and acceptance, vs alternative split-file approaches (e.g., Kiro's `requirements.md` / `design.md` / `tasks.md`). Skill-driven plugin layered on `flowctl` Python plumbing; the host agent (Claude Code / Codex / Droid / OpenCode) IS the intelligence, and flowctl provides only thin atomic helpers. Everything lives in the repo under `.flow/` — no external services, no global config, no SaaS. Uninstall: delete the directory.

Opt-in convenience skills (e.g. `/flow-next:map` wrapping `clawpatch`) may carry their own runtime prerequisites, but `flowctl` core never imports or requires them — the zero-dep contract holds for the base install; opt-in skills add nothing to the uninstall path beyond a single self-contained directory.

## Who it's for

Solo developers running multi-agent loops who need re-anchoring + receipts to keep agents on track overnight. Engineering teams adopting spec-driven development who need an artefact chain that replaces standups / refinement / design-review touchpoints. Platform owners building autonomous agent harnesses (Ralph) who need cross-model review gates and proof-of-work receipts. Also flow-swarm operators (in-progress companion product reading `.flow/specs/` natively).

## Key metrics

- **Smoke-test surface and parity.** Number of smoke suites × OS matrix (currently 7 × Linux/macOS/Windows). Cross-platform parity with Codex / Droid / OpenCode is non-negotiable.
- **Slash-command count and density.** Each command is a discrete handover. v0.42.0 ships 18; v1.0 holds the line on count while renaming `epic-review` → `spec-completion-review`.
- **Community-port adoption.** FlowFactory (Droid), flow-next-opencode (OpenCode) — independent ports validate the architecture without the maintainer.
- **Spec-driven adoption signal.** Inbound traffic to `docs/teams.md` and the AI-x-SDLC-Starter-Kit cross-link as proxy for team adoption.
- **Idea-to-merge wall-clock.** Time from `/flow-next:capture` to `/flow-next:make-pr` body landing on a draft PR. Worth measuring as the system matures.

## Tracks

### v1.0 vocabulary stability

The fn-43 epic→spec rename + alias deprecation timeline. The single highest-leverage cleanup before flow-next commits to a 1.0 contract. Backward compat for 0.x users is non-negotiable: aliases live until 2.0; opt-in migration with a flow-swarm carrot; never silent.

### Spec-driven team patterns

`docs/teams.md` (handover objects, Spec-as-PR, parallel work from one spec, R-ID frozen-at-handover, symmetric interview, adoption ladder). Cross-linked from the AI-x-SDLC-Starter-Kit methodology guide. Establishes flow-next's identity as a methodology, not just a tool.

### Ralph autonomous mode

The overnight loop. Receipt-based proof-of-work gates every state transition; multi-model review at every handover; auto-block stuck tasks; iteration cap. Differentiator from "ralph-wiggum"-style autonomous loops that run open-loop without quality gates.

### flow-swarm preparation

The on-disk `.flow/specs/` layout that flow-swarm reads natively. fn-43's rename is the trigger; the carrot framing in the migration banner is honest because flow-swarm literally needs the renamed layout. Coordination with flow-swarm timing is upstream of fn-43 close.

### TUI

`flow-next-tui` for parallel-run monitoring. Already shipped (multi-tool parser adapters, ETA calculation, Ralph control integration in flight). Not the focus area but kept healthy.

### Cross-platform parity

First-class on Claude Code + OpenAI Codex + Factory Droid. Community port for OpenCode. Canonical skill files use Claude-native tool names; `sync-codex.sh` rewrites for the Codex mirror. Single source of truth.

## Milestones

- **2026-Q3 — flow-next 1.0.0.** fn-43 ships; alias layer covers all 0.x callers; flow-swarm gains a stable `.flow/` contract to build against.
- **TBD — flow-swarm v1.** Reads `.flow/specs/` directly; coordinates parallel agents across worktrees; consumes flow-next's PR-as-cognitive-aid output.
- **TBD — Spec-driven team adoption case study.** First public team writeup using the methodology guide. Validates the framing externally.

## Not working on

- Hosted dashboards or SaaS tier. The whole architecture is "everything in the repo"; a hosted layer breaks the uninstall promise (`rm -rf .flow/`).
- Built-in CI runners. CI is the user's; flowctl provides `validate --all` for pipeline integration but does not run the pipeline.
- A graphical builder. The host agent IS the UI — adding a separate GUI splits the maintenance surface for negative product value.
- Replacing Jira / Linear for human-only teams. flow-next is for agentic-engineering teams; teams without agents should keep their existing tracker.
- Localization of CLI strings or skill workflow text. English-only through 1.x.
