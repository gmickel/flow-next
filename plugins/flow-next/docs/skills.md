# Skills catalog

Every stable skill flow-next ships, in one table. 32 skills: 27 slash-command-triggered (`/flow-next:<name>`) and 5 phrase-triggered. A phrase-triggered skill has no command file: describe what you want and the host agent matches the skill description, and on hosts that surface skills as commands it is also invocable by full skill name (`/flow-next:flow-next-worktree-kit`). Each row links the canonical `SKILL.md`.

One surface ships without a row here, on purpose: `/flow-next:uninstall` is a command with no skill behind it.

> Lifecycle position and narrative for the core commands: [root README - How the flow works](../../../README.md#how-the-flow-works). Slash commands also appear in the [root README - Commands table](../../../README.md#commands) with flags and opt-in notes.

## Lifecycle skills

The idea-to-merge pipeline, in order. Chart and guide sit **upstream of capture** and are optional - never mandatory stages.

| Skill | Trigger | What it does |
|---|---|---|
| [`flow-next-strategy`](../skills/flow-next-strategy/SKILL.md) | `/flow-next:strategy` | Create or maintain repo-root `STRATEGY.md` - target problem, approach, who it's for, key metrics, active tracks. Downstream skills read it for grounding. |
| [`flow-next-prospect`](../skills/flow-next-prospect/SKILL.md) | `/flow-next:prospect` | Generate ranked candidate ideas grounded in the repo, upstream of capture/plan. Optional focus hint (concept, path, constraint, volume). |
| [`flow-next-guide`](../skills/flow-next-guide/SKILL.md) | `/flow-next:guide` | Prompt-first router: recommends the **smallest sufficient** next workflow from the starting state (when to chart, skip chart, capture, interview, plan, or direct change). Stateless - no flowctl mutations. Use when unsure which pre-build stage applies. |
| [`flow-next-chart`](../skills/flow-next-chart/SKILL.md) | `/flow-next:chart` | **Optional** pre-capture decision-map discovery for **one** oversized/unclear idea. Grounds a bounded snapshot, resolves **one decision (D-ID) per invocation**, re-charts the frontier, emits a briefing for capture. Never writes a spec, never sets `ready`. Skip when intent is already stateable. |
| [`flow-next-capture`](../skills/flow-next-capture/SKILL.md) | `/flow-next:capture` | Synthesize the current conversation (or chart briefing) into a spec - source-tagged acceptance criteria (`[user]` / `[paraphrase]` / `[inferred]`), mandatory read-back before write. Chart handoff preserves D-ID/evidence links; criterion tags apply only to newly authored bullets. |
| [`flow-next-interview`](../skills/flow-next-interview/SKILL.md) | `/flow-next:interview` | Deep Q&A over a spec or task to extract complete detail - lead-with-recommendation, confidence tiers, codebase-first investigation; `--scope=business\|technical\|both`. |
| [`flow-next-plan`](../skills/flow-next-plan/SKILL.md) | `/flow-next:plan` | Research the codebase via parallel scouts, then break a spec into dependency-ordered, context-fit tasks. Writes the plan, never code. |
| [`flow-next-plan-review`](../skills/flow-next-plan-review/SKILL.md) | `/flow-next:plan-review` | Carmack-level cross-model review of a spec or plan (RepoPrompt / Codex / Copilot / Cursor backend). |
| [`flow-next-work`](../skills/flow-next-work/SKILL.md) | `/flow-next:work` | Execute a spec or task - git setup, fresh-context worker subagents, re-anchoring, quality checks, commits, evidence. Implementation offload is a routing decision you write, not a packaged mode - see [`orchestration.md`](orchestration.md#implementation-offload-the-bridge-route). |
| [`flow-next-impl-review`](../skills/flow-next-impl-review/SKILL.md) | `/flow-next:impl-review` | Carmack-level cross-model implementation review - confidence anchors, introduced-vs-pre-existing classification, SHIP / NEEDS_WORK receipt. On codex and host the first round fans out three axis draws (correctness / contracts / integration) merged into one fix pass - one round against the cap; steered by prose ("use 1 reviewer instead of 3"), never a config key. |
| [`flow-next-spec-completion-review`](../skills/flow-next-spec-completion-review/SKILL.md) | `/flow-next:spec-completion-review` | End-of-spec gate - verifies the *combined* implementation across all tasks satisfies the spec. |
| [`flow-next-qa`](../skills/flow-next-qa/SKILL.md) | `/flow-next:qa` | Live-app real-user QA derived from the spec - drives the running app via `flow-next-drive`, files P0/P1/P2 findings with evidence, YES/NO ship verdict receipt. Consumes `.flow/features/` navigation when present. Forbidden from marking PASS by reading source. Opt-in. |
| [`flow-next-make-pr`](../skills/flow-next-make-pr/SKILL.md) | `/flow-next:make-pr` | Render a cognitive-aid PR body from nine input streams and open via `gh` (create call interposable via `FLOW_PR_CREATE_CMD` for App/bot-authored PRs); with HTML artifact mode on, also commits a `pr.html` review instrument. |
| [`flow-next-resolve-pr`](../skills/flow-next-resolve-pr/SKILL.md) | `/flow-next:resolve-pr` | Resolve PR review feedback - fetch unresolved threads, triage, dispatch per-thread resolver agents, validate, commit, reply + resolve via GraphQL. |

## Autonomous loops

| Skill | Trigger | What it does |
|---|---|---|
| [`flow-next-pilot`](../skills/flow-next-pilot/SKILL.md) | `/flow-next:pilot` | Single-tick build-loop conductor - advances one *ready* spec by one pipeline stage per tick, ends with a `PILOT_VERDICT` line; your host's `/loop` or `/goal` owns iteration. |
| [`flow-next-land`](../skills/flow-next-land/SKILL.md) | `/flow-next:land` | Cadence-tick ship loop - babysits build-loop-authored PRs through CI fixes, review convergence, gated explicit merge (merge call interposable via `FLOW_PR_MERGE_CMD` for App/bot-performed merges), spec close, and release-follow; ends with a `LAND_VERDICT` line. |
| [`flow-next-ralph-init`](../skills/flow-next-ralph-init/SKILL.md) | `/flow-next:ralph-init` | **Deprecated** - prefer a script calling `/flow-next:pilot` + `/flow-next:land` ([why](running-lean.md#ralph-deprecated)); existing installs keep working. Scaffold the repo-local Ralph hardened harness under `scripts/ralph/` - external shell loop, fresh session per iteration, hook guardrails, receipts. |

## Knowledge & maintenance

| Skill | Trigger | What it does |
|---|---|---|
| [`flow-next-prime`](../skills/flow-next-prime/SKILL.md) | `/flow-next:prime` | Opinionated codebase assessment - classifies the project (lifecycle / topology / size / stack / delivery shape), probes size/legibility + operability with bounded deterministic evidence (the `flowctl prime classify` emitter), judges **substance not existence**, and leads with an operability verdict + ranked next-actions instead of a bare level. Scans the pillars as the evidence layer, verifies commands actually run, checks GitHub settings, fixes agent readiness with consent. `--classify-only` = cheap portfolio-triage sweep across many repos. |
| [`flow-next-visual`](../skills/flow-next-visual/SKILL.md) | `/flow-next:visual` | Restate a spec, a task, a diff range, or the current topic as a compact markdown digest - task tree, planned file-layout diff, R-ID coverage, shape sketches. Read-only, chat output only; a lighter register than the opt-in HTML render lenses. |
| [`flow-next-prose`](../skills/flow-next-prose/SKILL.md) | `/flow-next:prose` | Apply the artifact prose contract ([`prose.md`](prose.md)) to a substantial reply, report, or summary at draft time. Scoped to chat prose - short turns, tool narration, the visual digest, and file/PR/tracker output stay out (those artifact surfaces carry their own pointers). |
| [`flow-next-audit`](../skills/flow-next-audit/SKILL.md) | `/flow-next:audit` | Memory garbage collection - review each `.flow/memory/` entry against current code; Keep / Update / Consolidate / Replace / Delete / Harden. |
| [`flow-next-features`](../skills/flow-next-features/SKILL.md) | `/flow-next:features` | Seed or maintain the committed user-POV drive map at `.flow/features/` so QA and drive reuse how a user reaches each feature. Distinct from `/flow-next:map` (code index). Never a pipeline stage. |
| [`flow-next-memory-migrate`](../skills/flow-next-memory-migrate/SKILL.md) | `/flow-next:memory-migrate` | Lift the legacy flat memory files that predate the categorized YAML schema into it. |
| [`flow-next-sync`](../skills/flow-next-sync/SKILL.md) | `/flow-next:sync` | Plan-sync - update downstream task specs after implementation drift. Distinct from `tracker-sync`. |
| [`flow-next-tracker-sync`](../skills/flow-next-tracker-sync/SKILL.md) | `/flow-next:tracker-sync` | Project a spec to a Linear/GitHub/GitLab/Jira issue and reconcile body/status/comments two-way - projection, not coordination; the spec stays the source of truth. |
| [`flow-next-map`](../skills/flow-next-map/SKILL.md) | `/flow-next:map` | Optional - wrap `clawpatch map` for a semantic feature index at `.clawpatch/features/*.json`; scouts read it when present, fall back to grep/glob when absent. |
| [`flow-next-setup`](../skills/flow-next-setup/SKILL.md) | `/flow-next:setup` | Per-project setup - `.flow/` init, local flowctl install, CLAUDE.md/AGENTS.md instructions, review-backend + config ceremony, optional model-routing scaffold, optional `.flow/criteria.md` scaffold. |

## Phrase-triggered skills

No slash command - just describe what you want.

| Skill | Say something like | What it does |
|---|---|---|
| [`flow-next`](../skills/flow-next/SKILL.md) | "show me my tasks", "what's ready?", "list specs" | Day-to-day `.flow/` task and spec management via flowctl. |
| [`flow-next-deps`](../skills/flow-next-deps/SKILL.md) | "what's blocking what?", "execution order", "critical path" | Spec dependency graph and execution order - which specs can run in parallel. |
| [`flow-next-drive`](../skills/flow-next-drive/SKILL.md) | "drive the app", "verify the deployed UI" | Drive any UI surface like a real user - web, Electron/WebView2 over CDP, or native via the Cua Driver (MIT, provider-agnostic, background) / Computer Use, with a Cua Sandbox rung for headless/CI native runs. Surface-aware driver ladder; powers `/flow-next:qa`. Consumes `.flow/features/` navigation when present. |
| [`flow-next-export-context`](../skills/flow-next-export-context/SKILL.md) | "export context for external review" | Export RepoPrompt context to markdown for review with an external LLM (ChatGPT, Claude web, …). |
| [`flow-next-worktree-kit`](../skills/flow-next-worktree-kit/SKILL.md) | "create a worktree for …" | Git worktree create/list/switch/cleanup + `.env` copying - parallel feature work, isolated review; initializes or safely extends `.worktrees/.gitignore` so nested worktrees cannot be staged as gitlinks. |

## See also

- [Root README - Commands](../../../README.md#commands) - the slash-command table with flags and opt-in notes.
- [`README.md`](README.md) - the doc index (subsystem + workflow references).
- [`../../../agent_docs/adding-skills.md`](../../../agent_docs/adding-skills.md) - how to add a new skill (the three-edit rule).
