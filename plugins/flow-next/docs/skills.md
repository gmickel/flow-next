# Skills catalog

Every skill flow-next ships, in one table. 28 skills: 22 slash-command-triggered (`/flow-next:<name>`), 6 phrase-triggered (no command file — describe what you want and the host agent matches the skill description). Each row links the canonical `SKILL.md`.

> Lifecycle position and narrative for the core commands: [root README — How the flow works](../../../README.md#how-the-flow-works). Slash commands also appear in the [root README — Commands table](../../../README.md#commands) with flags and opt-in notes.

## Lifecycle skills

The spec-to-merge pipeline, in order.

| Skill | Trigger | What it does |
|---|---|---|
| [`flow-next-strategy`](../skills/flow-next-strategy/SKILL.md) | `/flow-next:strategy` | Create or maintain repo-root `STRATEGY.md` — target problem, approach, who it's for, key metrics, active tracks. Downstream skills read it for grounding. |
| [`flow-next-prospect`](../skills/flow-next-prospect/SKILL.md) | `/flow-next:prospect` | Generate ranked candidate ideas grounded in the repo, upstream of capture/plan. Optional focus hint (concept, path, constraint, volume). |
| [`flow-next-capture`](../skills/flow-next-capture/SKILL.md) | `/flow-next:capture` | Synthesize the current conversation into a spec — source-tagged acceptance criteria (`[user]` / `[paraphrase]` / `[inferred]`), mandatory read-back before write. |
| [`flow-next-interview`](../skills/flow-next-interview/SKILL.md) | `/flow-next:interview` | Deep Q&A over a spec or task to extract complete detail — lead-with-recommendation, confidence tiers, codebase-first investigation; `--scope=business\|technical\|both`. |
| [`flow-next-plan`](../skills/flow-next-plan/SKILL.md) | `/flow-next:plan` | Research the codebase via parallel scouts, then break a spec into dependency-ordered, context-fit tasks. Writes the plan, never code. |
| [`flow-next-plan-review`](../skills/flow-next-plan-review/SKILL.md) | `/flow-next:plan-review` | Carmack-level cross-model review of a spec or plan (RepoPrompt / Codex / Copilot backend). |
| [`flow-next-work`](../skills/flow-next-work/SKILL.md) | `/flow-next:work` | Execute a spec or task — git setup, fresh-context worker subagents, re-anchoring, quality checks, commits, evidence. Opt-in `delegate:codex` implementation offload. |
| [`flow-next-impl-review`](../skills/flow-next-impl-review/SKILL.md) | `/flow-next:impl-review` | Carmack-level cross-model implementation review — confidence anchors, introduced-vs-pre-existing classification, SHIP / NEEDS_WORK receipt. |
| [`flow-next-spec-completion-review`](../skills/flow-next-spec-completion-review/SKILL.md) | `/flow-next:spec-completion-review` | End-of-spec gate — verifies the *combined* implementation across all tasks satisfies the spec. |
| [`flow-next-qa`](../skills/flow-next-qa/SKILL.md) | `/flow-next:qa` | Live-app real-user QA derived from the spec — drives the running app via `flow-next-drive`, files P0/P1/P2 findings with evidence, YES/NO ship verdict receipt. Forbidden from marking PASS by reading source. Opt-in. |
| [`flow-next-make-pr`](../skills/flow-next-make-pr/SKILL.md) | `/flow-next:make-pr` | Render a cognitive-aid PR body from nine input streams and open via `gh`; with HTML artifact mode on, also commits a `pr.html` review instrument. |
| [`flow-next-resolve-pr`](../skills/flow-next-resolve-pr/SKILL.md) | `/flow-next:resolve-pr` | Resolve PR review feedback — fetch unresolved threads, triage, dispatch per-thread resolver agents, validate, commit, reply + resolve via GraphQL. |

## Autonomous loops

| Skill | Trigger | What it does |
|---|---|---|
| [`flow-next-pilot`](../skills/flow-next-pilot/SKILL.md) | `/flow-next:pilot` | Single-tick build-loop conductor — advances one *ready* spec by one pipeline stage per tick, ends with a `PILOT_VERDICT` line; your host's `/loop` or `/goal` owns iteration. |
| [`flow-next-land`](../skills/flow-next-land/SKILL.md) | `/flow-next:land` | Cadence-tick ship loop — babysits build-loop-authored PRs through CI fixes, review convergence, gated explicit merge, spec close, and release-follow; ends with a `LAND_VERDICT` line. |
| [`flow-next-ralph-init`](../skills/flow-next-ralph-init/SKILL.md) | `/flow-next:ralph-init` | Scaffold the repo-local Ralph hardened harness under `scripts/ralph/` — external shell loop, fresh session per iteration, hook guardrails, receipts. |

## Knowledge & maintenance

| Skill | Trigger | What it does |
|---|---|---|
| [`flow-next-prime`](../skills/flow-next-prime/SKILL.md) | `/flow-next:prime` | 8-pillar / 48-criteria agent-readiness assessment with parallel scouts — verifies commands actually run, checks GitHub settings, fixes agent readiness with consent. |
| [`flow-next-audit`](../skills/flow-next-audit/SKILL.md) | `/flow-next:audit` | Memory garbage collection — review each `.flow/memory/` entry against current code; Keep / Update / Consolidate / Replace / Delete. |
| [`flow-next-memory-migrate`](../skills/flow-next-memory-migrate/SKILL.md) | `/flow-next:memory-migrate` | Lift pre-fn-30 legacy flat memory files into the categorized YAML schema. |
| [`flow-next-sync`](../skills/flow-next-sync/SKILL.md) | `/flow-next:sync` | Plan-sync — update downstream task specs after implementation drift. Distinct from `tracker-sync`. |
| [`flow-next-tracker-sync`](../skills/flow-next-tracker-sync/SKILL.md) | `/flow-next:tracker-sync` | Project a spec to a Linear/GitHub issue and reconcile body/status/comments two-way — projection, not coordination; the spec stays the source of truth. |
| [`flow-next-map`](../skills/flow-next-map/SKILL.md) | `/flow-next:map` | Optional — wrap `clawpatch map` for a semantic feature index at `.clawpatch/features/*.json`; scouts read it when present, fall back to grep/glob when absent. |
| [`flow-next-setup`](../skills/flow-next-setup/SKILL.md) | `/flow-next:setup` | Per-project setup — `.flow/` init, local flowctl install, CLAUDE.md/AGENTS.md instructions, review-backend + config ceremony. |

## Phrase-triggered skills

No slash command — just describe what you want.

| Skill | Say something like | What it does |
|---|---|---|
| [`flow-next`](../skills/flow-next/SKILL.md) | "show me my tasks", "what's ready?", "list specs" | Day-to-day `.flow/` task and spec management via flowctl. |
| [`flow-next-deps`](../skills/flow-next-deps/SKILL.md) | "what's blocking what?", "execution order", "critical path" | Spec dependency graph and execution order — which specs can run in parallel. |
| [`flow-next-drive`](../skills/flow-next-drive/SKILL.md) | "drive the app", "verify the deployed UI" | Drive any UI surface like a real user — web, Electron/WebView2 over CDP, or native via the Cua Driver (MIT, provider-agnostic, background) / Computer Use, with a Cua Sandbox rung for headless/CI native runs. Surface-aware driver ladder; powers `/flow-next:qa`. |
| [`flow-next-export-context`](../skills/flow-next-export-context/SKILL.md) | "export context for external review" | Export RepoPrompt context to markdown for review with an external LLM (ChatGPT, Claude web, …). |
| [`flow-next-rp-explorer`](../skills/flow-next-rp-explorer/SKILL.md) | "use rp to find …" | Token-efficient codebase exploration through the RepoPrompt CLI. |
| [`flow-next-worktree-kit`](../skills/flow-next-worktree-kit/SKILL.md) | "create a worktree for …" | Git worktree create/list/switch/cleanup + `.env` copying — parallel feature work, isolated review. |

## See also

- [Root README — Commands](../../../README.md#commands) — the slash-command table with flags and opt-in notes.
- [`README.md`](README.md) — the doc index (subsystem + workflow references).
- [`../../../agent_docs/adding-skills.md`](../../../agent_docs/adding-skills.md) — how to add a new skill (the three-edit rule).
