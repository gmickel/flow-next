---
name: flow-next
last_updated: 2026-08-01
generator: flow-next-strategy
---

# flow-next Strategy

## Target problem

AI agent workflows drift, lose context, and produce uneven quality at scale. Existing task trackers (Jira, Linear) optimize for human cadence — 2-3 week implementations with daily standups, mid-flight refinement, and design reviews carrying the weight. Agentic engineering compresses implementation to hours, not weeks; the touchpoints that pre-agentic Agile relied on collapse, and the spec has to carry the full weight upstream. Without structured handovers between idea and merge, agents drift mid-task, reviewers face 10K-line diffs with no focus signal, and quality is uneven across runs.

## Our approach

Spec-driven development with re-anchoring, cross-model review, and zero external dependencies. Six named handover objects between idea and merge — each reviewable on its own, cross-model-verified, and frozen at handover. **Specs are single durable documents that evolve through layers** — `.flow/specs/<id>.md` is the source of truth for goal, architecture, R-IDs, and acceptance, vs alternative split-file approaches (e.g., Kiro's `requirements.md` / `design.md` / `tasks.md`). Skill-driven plugin layered on `flowctl` Python plumbing; the host agent IS the intelligence (first-class on Claude Code, OpenAI Codex, Factory Droid, Cursor, xAI Grok Build, and OpenCode - canonical sentence in `plugins/flow-next/docs/platforms.md`), and flowctl provides only thin atomic helpers. Everything lives in the repo under `.flow/` — no external services, no global config, no SaaS. Uninstall: delete the directory.

Opt-in convenience skills (e.g. `/flow-next:map` wrapping `clawpatch`) may carry their own runtime prerequisites, but `flowctl` core never imports or requires them — the zero-dep contract holds for the base install; opt-in skills add nothing to the uninstall path beyond a single self-contained directory.

## Design principles

Standing rules that decide day-to-day build questions. Each earned its place through a shipped decision; the anchors are the receipts.

- **The artifact is the contract.** Nothing between the plan and an executor restates content that lives in a file - prompts carry pointers and rails; every executor (native worker, bridged CLI, scout, runner) reads the spec/task files as its brief. Quality budget therefore concentrates at plan time, where the session model writes the spec; a thin artifact is refused downstream (the worker's thin-task valve), never compensated for. *(Anchor: fn-103 / decision record `composed-brief-deleted-path-handoff-2026-07-19` - an 8-run eval deleted the composed delegation brief.)*
  - **The reviewer is an executor too - identities, not payloads.** A review prompt carries the rubric, a `<base-sha>..<head-sha>` range, resolvable paths, and the reply grammar; it never carries the diff body, the spec body, or re-rendered prior findings. The reviewer has a shell and a checkout and already fetches. Two consequences that are not negotiable: a prompt-payload *fitter* or *truncator* is evidence the payload is wrong (a genuine transport cap is a separate thing and is named as transport), and prior findings come from session continuity or a receipt path, never a re-render. This was decided once in fn-74, re-accreted twice by fn-90 and fn-159, and cost a false-SHIP hole plus reviewers seeing ~10% of a 495 KB diff - so it is enforced by a test, not by prose. *(Anchor: fn-169; the re-accretion history is the argument.)*
- **flowctl grows only under burden of proof.** flowctl is thin atomic plumbing - hashes, path membership, schema validation, receipts, git mechanics. A subcommand is added only when the operation involves zero judgment and must work with no agent in the loop; anything that reads, weighs, or decides belongs to the host agent. Deterministic proxies for judgment questions are banned outright *(anchor: `plan-sync-skip-gate-not-viable-2026-07-03`)*; the periodic audit that keeps this honest is the fn-101 pattern - classify every subcommand keep / leakage / vestigial, burden of proof on keeping, and on adding.
- **Remember the bitter lesson.** Do not build scaffolding around a model's current weaknesses - capability grows and the scaffolding rots into cost (the composed brief was exactly this). Before adding a compensating mechanism, try stating the bar in one general sentence; before keeping one, eval it against its absence with pre-registered bars and delete on evidence. Deterministic machinery is reserved for what models should never own regardless of capability: unattended-trust rails (receipts, rollback, guard shapes, schemas), not quality compensation.
- **Receipts are the portable product boundary.** Downstream tools consume versioned, additive receipt fields with explicit identity, snapshot binding, lineage, bounds, and labeled fallback. They never depend on Flow-Next's parser or skill internals, and they never turn stale or ambiguous evidence into current state. *(Anchors: fn-136 structured findings 3.9.0; fn-137 criteria compliance receipts 3.10.0; fn-138 published config schema 3.12.0 - the principle graduated from aspiration to receipted rule.)*

## Who it's for

Solo developers running multi-agent loops who need re-anchoring + receipts to keep agents on track overnight. Engineering teams adopting spec-driven development who need an artefact chain that replaces standups / refinement / design-review touchpoints. Platform owners building autonomous agent harnesses (Ralph) who need cross-model review gates and proof-of-work receipts. Also flow-swarm operators (in-progress companion product reading `.flow/specs/` natively).

## Key metrics

- **Smoke-test surface and parity.** Number of smoke suites × OS matrix (currently 10 × Linux/macOS/Windows, plus Cursor-install, python-probe, and Windows-launcher jobs). Cross-platform parity across Codex / Droid / Cursor / Grok Build (and the OpenCode install path) is non-negotiable.
- **Slash-command count and density.** Each command is a discrete handover. 23 commands / 28 skills / 21 subagents at 3.12.0; additions must justify a new handover, not a convenience alias (the retired `epic-review` alias was removed entirely in 3.3.1).
- **OpenCode-path adoption.** The in-repo `install-opencode.sh` is the OpenCode adoption signal (the flow-next-opencode port is superseded and archived as a pointer); FlowFactory predates native first-class Droid support and is historical evidence, not the current Droid story.
- **Spec-driven adoption signal.** Inbound traffic to `docs/teams.md` and the AI-x-SDLC-Starter-Kit cross-link as proxy for team adoption.
- **Idea-to-merge wall-clock.** Time from `/flow-next:capture` to `/flow-next:make-pr` body landing on a draft PR. Worth measuring as the system matures.

## Tracks

### v1.0 vocabulary stability (SHIPPED)

Complete. fn-43 (epic→spec rename) shipped in 1.0.0 (2026-05-09) with the full alias layer; the aliases outlived the original "until 2.0" plan and were removed telemetry-driven in 3.0.0 (fn-111) along with the pre-1.0 migration machinery. Kept as history because the contract it established - canonical vocabulary, never-silent migration - still governs renames.

### Spec-driven team patterns

`docs/teams.md` (handover objects, Spec-as-PR, parallel work from one spec, R-ID frozen-at-handover, symmetric interview, adoption ladder, and since 3.10.0 standing project-wide criteria: a user-owned `.flow/criteria.md` of G-IDs judged by the completion review on every spec). Cross-linked from the AI-x-SDLC-Starter-Kit methodology guide. Establishes flow-next's identity as a methodology, not just a tool.

### Ralph autonomous mode

The autonomy track — a three-loop suite (pilot 1.13.0, land 1.14.0, Ralph fully opt-in with zero default hooks since 3.0.0/fn-114; land gained the structural authorship marker and the FLOW_PR_CREATE_CMD identity seam in 3.11.0). **Pilot + land are the default path**: pilot builds (ready spec → plan → reviews → work → `[opt-in qa]` → draft PR, host `/loop`/`/goal` drives the ticks), land ships (draft PR → CI-fixed → review-converged → gated merge → spec close → release-follow); run concurrently in separate clones they form the full assembly line, with the readiness gate / tracker board as the consent boundary. An **optional live-app QA stage** (`pipeline.qa`, default off, fn-72) sits between work and make-pr: with it on, pilot drives the running build like a real user at all-tasks-done and surfaces runtime/UI breakage into the draft PR — autonomy-safe (never prompts, never hard-blocks; `NEEDS_WORK` still advances), and it **augments, never replaces** CI/staging/manual QA. An **opt-in backlog mode** (`pilot.autonomy=backlog`, default off, fn-68) widens pilot from "one already-ready spec" to **standing management of the whole open backlog** — per tick it enumerates flow specs + tracker issues, triages the top dep-ordered item, and either advances it or surfaces a precise async question; this pushes the consent boundary from *before* the loop to *inside the loop, on block*, while holding the line that backlog mode **never authors a spec** (a thin/missing spec is a surfaced "needs capture/interview" gap), **never promotes** (the human's board act), and **never merges** (land stays human-gated). Readiness stays the human's explicit signal (ready gate / board state), never an agent-inferred score. The per-tick **decision log** (`flowctl pilot-log`) is the factory-efficiency readout and the self-improvement substrate. Ralph is now **deprecated**: it predates the orchestration primitives that replace it, and a script calling pilot + land under a host loop or `cron` covers the same ground without the `scripts/ralph/` scaffold, the guard-hook registration, or the second receipt plumbing. Nothing is removed, existing installs keep working, and `docs/ralph.md` stays maintained as their reference; the track's forward investment is pilot + land. The same pass deprecated packaged codex delegation (`work.delegate*`, fn-55) in favor of the agentic route — the setup CLAUDE.md routing scaffold plus the `flowctl usage` bridge recipes — and `flow-98` then removed it outright. Both deprecations are documented in `docs/running-lean.md`, which also names the human-driven and autonomous **operating profiles** and prices every optional layer so running lean is a deliberate choice rather than a missing setup. Quality discipline is invariant across all: multi-model review at every handover, convergence-aware review terminals (trajectory-based early escalation plus reviewer-emitted `NEEDS_HUMAN`), don't-thrash reflexes (two-strike unready / auto-block / bounded CI fixes), evidence over narration, surface-don't-force. Differentiator from "ralph-wiggum"-style autonomous loops that run open-loop without quality gates. The cloud-orchestration role (scheduler, hosted environments, multi-agent-at-scale, the production monitor→triage loop) is **mergefoundry's**, not flow-next's — fn-68 is the governed, in-repo per-tick conductor such a control plane invokes. (Track name kept for spec-tag stability; it covers the whole loop suite.)

### flow-swarm preparation (contract pillars SHIPPED)

The portable-contract surface flow-swarm consumes without importing Flow-Next internals is now shipped: structured review findings with durable IDs, snapshot-bound anchors, and explicit currentness (fn-136, 3.9.0); per-criterion compliance in ordinary receipts (fn-137, 3.10.0); and a published JSON Schema for the full config surface at flow-next.dev/schema/ (fn-138, 3.12.0). Legacy prose remains a safe labeled fallback throughout. Open coordination fact: flow-swarm still reads the pre-1.0 `epics` JSON key and forwards `--epic` flags (flagged at 3.0.0) and must migrate to the canonical spec surface. Coordination timing remains downstream product work; Flow-Next owns the stable handover objects.

### Tracker determinism

The fn-139-141 batch (3.5.2-3.6.1): the four-provider tracker bridge's repeatable machinery - auth boundaries, provider selection, pagination, create-if-unlinked, status transitions, relations, PR links, comment-marker dedup, locks, one aggregate receipt - moved from skill prose into the deterministic `flowctl_tracker/` package, deleting four growing per-provider API recipes and cutting reached-path prose ~70%. Every semantic judgment (discovery, three-way body conflicts, lifecycle-comment content, structured recovery) stays in the host; the facade supersedes fn-57 R3's prohibition on tracker mutations in flowctl because the mutations carry zero judgment. The template for future "prose that grew into plumbing" extractions.

### TUI

`flow-next-tui` for parallel-run monitoring. Already shipped (multi-tool parser adapters, ETA calculation, Ralph control integration in flight). Not the focus area but kept healthy.

### Cross-platform parity

First-class on Claude Code, OpenAI Codex, Factory Droid, Cursor (3.3.0), xAI Grok Build (3.4.0), and OpenCode (4.3.0, installer-delivered); (canonical roster sentence: `plugins/flow-next/docs/platforms.md`). Canonical skill files use Claude-native tool names; `sync-codex.sh` rewrites for the Codex mirror; Cursor/Droid/Grok consume canonical files as-is, so Claude-only references need portable fallbacks. What parity means mechanically: the fn-121 plugin-vs-copy setup modes and the fn-139 tracker-manifest install-integrity contract. Single source of truth.

### Self-improving through normal work

The system compounds as a side-effect of normal use — memory accretes from review fix-cycles, the glossary is seeded by prime and grows through interview/capture while plan/work/review read it back, decision records land when judgment calls happen, and strategy drift is surfaced by the skills that consume the doc. Never a manual compound/refresh ceremony: improvement that depends on remembering an extra command doesn't happen. Audit is the garbage collector, not the growth mechanism.

## Milestones

- **DONE 2026-05-09 — flow-next 1.0.0** (shipped early, Q2). fn-43 + alias layer; the stable `.flow/` contract flow-swarm needed. Since then: 2.0.0 (2026-06-12, render lenses), 3.0.0 (2026-07-21, alias removal + Ralph opt-in + dead-surface sweep), 3.12.0 (2026-07-31, the fn-136/137/138 portable-contract series complete).
- **Next — flow-swarm contract consumption.** flow-swarm migrates off the `epics` key and renders structured findings + criteria compliance from receipts; first end-to-end swarm-driven pipeline run against a published-schema config.
- **TBD — flow-swarm v1.** Reads `.flow/specs/` directly; coordinates parallel agents across worktrees; consumes the PR-as-cognitive-aid walkthrough (the portable contract for it shipped in fn-136).
- **TBD — Spec-driven team adoption case study.** First public team writeup using the methodology guide. Validates the framing externally.

## Not working on

- Hosted dashboards or SaaS tier. The whole architecture is "everything in the repo"; a hosted layer breaks the uninstall promise (`rm -rf .flow/`).
- Built-in CI runners. CI is the user's; flowctl provides `validate --all` for pipeline integration but does not run the pipeline.
- A graphical builder. The host agent IS the UI — adding a separate GUI splits the maintenance surface for negative product value.
- Replacing Jira / Linear for human-only teams. flow-next is for agentic-engineering teams; teams without agents should keep their existing tracker.
- Localization of CLI strings or skill workflow text. English-only through 1.x.
