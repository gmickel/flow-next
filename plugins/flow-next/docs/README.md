# Flow-Next docs

The offline-resilient reference for flow-next — **repeatable agentic engineering**: durable specs, re-anchored workers, adversarial reviews, receipts. Each file here is self-contained, terse, and offline-readable. Cross-links use relative repo paths — fork-survivable, no external URLs.

**Start here by intent:**

- *"What is this and how do I install it?"* → [root README](../../../README.md) — pitch, tenets, install, 5-command happy path.
- *"What skills exist?"* → [`skills.md`](skills.md) - all 30 skills, triggers, one-liners.
- *"How do we adopt this as a team?"* → [`teams.md`](teams.md) — handover objects, Spec-as-PR, adoption ladder.
- *"How do I run it autonomously?"* → [`ralph.md`](ralph.md) + the pilot/land skill pages below.
- *"Which model does what, and how do I change that?"* → [`orchestration.md`](orchestration.md) - routing surfaces, steering, CLAUDE.md model tables, loop chaining (including unattended chart driving).
- *"What's every flag on every command?"* → [`flowctl.md`](flowctl.md) (includes the full `flowctl chart` contract).
- *"This idea is too big / still unclear before capture?"* → [`../skills/flow-next-chart/SKILL.md`](../skills/flow-next-chart/SKILL.md) - optional `/flow-next:chart` decision-map discovery; never mandatory.
- *"Not sure which pre-build path is smallest?"* → [`../skills/flow-next-guide/SKILL.md`](../skills/flow-next-guide/SKILL.md) - `/flow-next:guide` router.

> For the repo's strategic intent see [`../../../STRATEGY.md`](../../../STRATEGY.md). For canonical vocabulary (Spec, Chart, D-ID, R-ID, Handover object, Receipt, render lens, …) see [`../../../GLOSSARY.md`](../../../GLOSSARY.md).

## Subsystem references

| Doc | What's in it |
|-----|--------------|
| [`architecture.md`](architecture.md) | `.flow/` directory layout (specs, tasks, **charts**), spec-first task model, ID format (shared `fn-N` domain with charts), separation of concerns, task completion shape |
| [`skills.md`](skills.md) | Skills catalog - all 30 skills (24 slash-command, 6 phrase-triggered), grouped by lifecycle / autonomy / maintenance, each linked to its `SKILL.md` (includes optional chart + guide) |
| [`spec-template.md`](spec-template.md) | Canonical scaffold cross-link, **customizing the scaffold via root `SPEC.md`** (what is safe to change, what breaks), R-ID rules, confidence anchors, introduced-vs-pre-existing, protected artifacts, trivial-diff skip, receipt schema |
| [`review-findings.md`](review-findings.md) | Portable v1 structured-findings contract — canonical enums, durable IDs, snapshot-bound anchors, receipt lineage/currentness, bounds, memory relationship, and fail-safe consumer fallback |
| [`pr-cognitive-aid.md`](pr-cognitive-aid.md) | Portable v1 PR cognitive-aid contract — immutable artifact home, identity/currentness, cross-render semantic parity, canonical fixture, and byte-pinned downstream vendoring |
| [`memory-schema.md`](memory-schema.md) | Categorized memory tree (bug / knowledge tracks), frontmatter schemas, decisions subtree, audit lifecycle, legacy migration |
| [`tracker-sync.md`](tracker-sync.md) | `/flow-next:tracker-sync` bridge: projection-not-coordination, discovery ceremony, hybrid id model, sync-state schema, deterministic `flowctl tracker` transport and capabilities, lifecycle touchpoints, optional **chart lifecycle projection** (`tracker.charts`), Ralph-safe conflict queueing; distinct from `/flow-next:sync` (plan-sync) |
| [`html-artifacts.md`](html-artifacts.md) | Optional HTML artifact mode (2.0.0+) — `artifacts.html.enabled` activation, the shared disclosure reference, spec lens (capture §5.10 / plan Step 8.5, state-dependent rendering), PR lens (make-pr Phase 1.5, R-ID-verified review instrument), GitHub display limitation + commit-vs-gitignore, conversational regen, Lavish (`lavish-axi`) optional companion, autonomous generate-only discipline |
| [`glossary.md`](glossary.md) | Repo-root `GLOSSARY.md` shape, resolution walk, subcommands, R17 forbidden-vocabulary guard |
| [`strategy.md`](strategy.md) | Repo-root `STRATEGY.md` shape, Rumelt sections, foreign-file refusal, R19 fluff guard, how downstream skills consume it |
| [`self-improving.md`](self-improving.md) | How the system compounds through normal work — memory, glossary, decision records, strategy loops (seeded / grown / read / pruned); the no-manual-ceremony principle |
| [`platforms.md`](platforms.md) | Install matrix (Claude Code / Codex / Droid / OpenCode), cross-platform patterns, Codex model mapping, community ports, optional skill requirements (`/flow-next:map` Node 22+ + `clawpatch`) |
| [`sync-codex.md`](sync-codex.md) | `scripts/sync-codex.sh` pipeline shape, validation guards, plain-text transform (fn-45), R17 cross-link discipline |
| [`troubleshooting.md`](troubleshooting.md) | Reset stuck tasks, `.flow/` cleanup, Ralph debugging, receipt validation, RepoPrompt CLI conflict resolution, `/flow-next:map` clawpatch failure modes, uninstall |

## Workflow references

| Doc | What's in it |
|-----|--------------|
| [`flowctl.md`](flowctl.md) | Full `flowctl` CLI reference - every command, every flag, JSON shapes, exit codes (including the complete [`chart`](flowctl.md#chart) subcommand contract and the [`repo-map`](flowctl.md#repo-map) readers consumed by the `/flow-next:map` opt-in skill) |
| [`orchestration.md`](orchestration.md) | Orchestration & model routing - the steering principle (one-off / durable / config), subagent tiers, review-backend grammar + precedence, `delegate:codex`, per-spec backend fields, CLAUDE.md model-routing tables, pilot+land loop chaining, unattended chart driving (not a pilot stage), what stays fixed |
| [`../skills/flow-next-chart/SKILL.md`](../skills/flow-next-chart/SKILL.md) | `/flow-next:chart` - optional pre-capture decision-map discovery for one oversized/unclear idea. Adaptive loop (ground, one D-ID per invocation, re-chart); briefing handoff to capture; never writes specs or sets ready. |
| [`../skills/flow-next-guide/SKILL.md`](../skills/flow-next-guide/SKILL.md) | `/flow-next:guide` - prompt-first router that recommends the smallest sufficient workflow (when to chart, skip chart, capture, interview, plan, or direct change). Stateless. |
| [`../skills/flow-next-prime/SKILL.md`](../skills/flow-next-prime/SKILL.md) | `/flow-next:prime` - how ready is this repo for agents? Figures out what kind of project it is looking at (via the deterministic [`flowctl prime classify`](flowctl.md#prime-classify) emitter), then checks that build/test/lint commands **actually run** instead of trusting that config files exist, and answers with a verdict plus a ranked list of next actions. Deep reference files sit next to the skill (`classification.md`, `playbooks.md`, `stacks.md`, `harness.md`, `pillars.md`); `--classify-only` is a cheap triage sweep across many repos at once. No `docs/prime.md` page - [`skills.md`](skills.md) is the catalog surface. |
| [`../skills/flow-next-qa/SKILL.md`](../skills/flow-next-qa/SKILL.md) | `/flow-next:qa` — live-app real-user QA pass. Derives scenarios from the spec (AC / R-IDs / boundaries), drives the running app via [`flow-next-drive`](../skills/flow-next-drive/SKILL.md), files structured P0/P1/P2 findings with evidence, ends with a YES/NO ship verdict receipt (`type: qa_verdict`). FORBIDDEN from marking PASS by reading source. Runs user-invoked OR as the optional `pipeline.qa` pilot stage (default off, fn-72). **Augments — never replaces — CI/staging/manual QA**; requires a live deploy + a driver. |
| [`../skills/flow-next-pilot/SKILL.md`](../skills/flow-next-pilot/SKILL.md) | `/flow-next:pilot` — single-tick conductor for plan / plan-review / work / make-pr, plus an **optional `qa` stage** (`pipeline.qa==on`, default off, fn-72) at the all-tasks-done juncture before make-pr, and an **opt-in backlog mode** (`pilot.autonomy=backlog`, default off, fn-68) that widens selection from "one ready spec" to the whole open backlog (flow + tracker), triaging the top dep-ordered item and surfacing async questions when stuck — never authoring, never promoting, never merging. Covers `PILOT_VERDICT` grammar (incl. backlog `ASKED`), `mode:autonomous` signal, strikes ledger, driver recipes, and Ralph as the alternative driver — never nested. See [`references/backlog-mode.md`](../skills/flow-next-pilot/references/backlog-mode.md). |
| [`../skills/flow-next-land/SKILL.md`](../skills/flow-next-land/SKILL.md) | `/flow-next:land` — cadence-tick ship loop babysitting build-loop-authored PRs. Covers the `LAND_VERDICT` grammar, dual authorship signals, CI tri-state + fix budget, patience window, `land.reviewSignal`, the confined auto-merge override, post-merge tail (spec close → tracker → release-follow), and `--dry-run`. Opt-in. |
| [`ralph.md`](ralph.md) | Ralph autonomous mode internals — hooks, receipts, iteration cap, DCG setup, sandbox options |
| [`../skills/flow-next-work/references/codex-delegation.md`](../skills/flow-next-work/references/codex-delegation.md) | `/flow-next:work` opt-in Codex implementation-delegation — host pre-flight gates + one-time consent, `codex exec` invocation + result schema, orchestration split / one run per task / classification / safety, circuit breaker + Ralph-safe + ralph-guard amendment + receipts + attribution. OFF by default. |
| [`teams.md`](teams.md) | Spec-driven team workflow — handover objects, Spec-as-PR, parallel work from one spec, symmetric interview, adoption ladder |
| [`ci-workflow-example.yml`](ci-workflow-example.yml) | Drop-in GitHub Actions example running `flowctl validate --all` |

## Notable updates

Append-only list of **behavior-affecting changes and new opt-in defaults**. Newest first. Not a changelog — one line each, plus how to enable. Seeded by fn-134; later releases append.

**Format (keep this shape):**

```
- **`config.key` or feature name** — one-line what changed / why it matters. Enable: `command or config`. Details: [link](path).
```

- **A reopened chart keeps its capture door** - re-running `flowctl chart briefing` after a `chart reopen` with the same proposal over an unchanged ledger used to hand back the briefing the reopen had staled and call it a no-op, leaving a briefable chart with no capture-ready package and no obvious way to get one. The reopen now counts as a new epoch, so the same proposal mints the next package and names what it supersedes (`supersedes_stale` under `--json`; `(supersedes stale B1)` on the terminal line). Enable: nothing - it is what `chart briefing` now does after a reopen. Details: [`flowctl.md`](flowctl.md#chart), [`../skills/flow-next-chart/workflow.md`](../skills/flow-next-chart/workflow.md).
- **Review-round cap default raised 4 -> 8** - fix+re-review loops get twice the room before refusing and escalating to a human. Behavior at the cap is unchanged (refuse to dispatch, exit `4` + `ESCALATE:`, reset only on SHIP or `flowctl spec reset-review-rounds`). Enable: nothing; override with `MAX_REVIEW_ITERATIONS=<n>` (never zero, never disabled). Details: [`ralph.md`](ralph.md), [`flowctl.md`](flowctl.md).
- **`chart create --initial-map-file` refuses an ambiguous alias namespace (3.13.2)** - an explicit `id` colliding with another decision's generated alias (`<n>`, `d<n>`, or the full decision id) is now rejected with a `validation` / `alias_collision` error naming both claimants, instead of the last writer silently winning and every edge on that alias pointing at the wrong decision. Enable: nothing - it is the command's own validation. Details: [`flowctl.md`](flowctl.md#chart).
- **Chart's entry test - destination known, route unknown (3.13.1)** - a theme or direction ("make X more Y") is now refused before any grounding spend, because with no nameable end state there is no Outcome to state, no boundary that rules anything out of scope, and a map that never closes; chart offers a narrowing or `/flow-next:prospect` instead. Enable: nothing - it is the skill's own refusal path. Details: [`../skills/flow-next-chart/SKILL.md`](../skills/flow-next-chart/SKILL.md), [`../skills/flow-next-guide/SKILL.md`](../skills/flow-next-guide/SKILL.md).
- **`/flow-next:chart` + `/flow-next:guide` (fn-135)** - optional pre-capture decision-map discovery for oversized/unclear ideas, plus a smallest-sufficient router so chart never becomes a mandatory stage. Enable: nothing required for local chart work; optional tracker projection with `flowctl config set tracker.charts on` when the bridge is active. Details: [`../skills/flow-next-chart/SKILL.md`](../skills/flow-next-chart/SKILL.md), [`flowctl.md`](flowctl.md#chart), [`tracker-sync.md`](tracker-sync.md#chart-lifecycle-projection).
- **`FLOW_PR_CREATE_CMD` - make-pr's PR-create call is interposable** - repos that require App/bot-authored PRs (single-maintainer repos with a required approval, where GitHub forbids self-approving) point the env var at a wrapper that supplies its own identity; the wrapper receives make-pr's stable argument contract (`--title/--body-file/[--draft]/--base/--head`) and must print the PR URL. Unset = `gh pr create`, unchanged. Enable: `export FLOW_PR_CREATE_CMD=/path/to/wrapper`. Details: [`create-and-finalize.md`](../skills/flow-next-make-pr/create-and-finalize.md) § 4.6 (inline contract).
- **Standing project-wide acceptance criteria are now judged on every spec** - put team-wide rules in `.flow/criteria.md` (`- **G1:** ...`, the R-ID grammar at project scope) and the existing spec completion review judges each one, recording met/violated/n-a compliance in the ordinary review receipt. Absent file = zero effect anywhere. Enable: answer the `/flow-next:setup` "Global criteria" question, or create `.flow/criteria.md` yourself. Details: [`spec-template.md`](spec-template.md) § Global criteria, [`review-findings.md`](review-findings.md) § Global-criteria compliance.
- **Pull requests now guide the human review from intent to evidence** - logical steps explain why the change exists, group the files that belong together, name deliberate non-changes, and attach proof, while the separate review plan keeps attention on the decisions that still need human judgment. Enable: nothing to configure. Details: [`pr-cognitive-aid.md`](pr-cognitive-aid.md).
- **Review findings keep their identity across fix rounds** - current, resolved, and superseded findings stay distinguishable and traceable to the review that raised them, while existing prose receipts remain valid. Enable: nothing to configure. Details: [`review-findings.md`](review-findings.md).
- **Interview-authored criteria now say where they came from** - reviewers can distinguish what a person said from what the agent inferred, so the grounded-versus-guessed tally and targeted follow-up work on interview-authored specs. Enable: nothing to configure. Details: [`spec-template.md`](spec-template.md) § Source tags.
- **Interview now fills the spec sections your project adds** - mark a project-specific section with `<!-- scope: ... -->` and the matching interview pass owns it; other or unmarked sections stay preserved. Enable: add a scope marker to the section; no config. Details: [`spec-template.md`](spec-template.md) § Customizing the scaffold for your project.
- **Tracker status conflicts now follow the team's chosen policy** - `flow-wins` and `tracker-wins` take their documented paths, while `always-ask` keeps the conflict visible for human resolution. Existing default remains `always-ask`; configure with `flowctl config set tracker.conflictTiebreak flow-wins|tracker-wins|always-ask`. Details: [`tracker-sync.md`](tracker-sync.md) § Reconciliation - who-wins.
- **Reviewer sandbox is never widened, and a delivered verdict is never a transport failure** — the codex sandbox-failure message used to suggest `--sandbox danger-full-access` / `CODEX_SANDBOX`, which agents pattern-matched onto unrelated review failures and used to re-frame a `NEEDS_WORK` as retryable transport. Reviewers are read-only by contract, so a blocked reviewer is a prompt/scope bug (Windows still resolves via `auto`). No action needed; the review skills now carry the rule explicitly.
- **Tracker mutations now use one deterministic facade across GitHub, GitLab, Jira, and Linear** — lifecycle skills still decide semantic content and recovery choices, while `flowctl tracker` owns provider requests, pagination, idempotency, status policy, relation projection, and one aggregate receipt. No action needed for existing tracker configuration. Details: [`tracker-sync.md`](tracker-sync.md) § Lifecycle facade.
- **`.flow/` writes refuse symlinked components** — `flowctl` no longer writes through a symlink anywhere between `.flow` and the file it is writing, so an untrusted checkout cannot redirect a write outside the workspace or onto another managed file. A legitimately symlinked `.flow` **directory** is still supported. No action needed; if a run now reports a refused path, replace that symlink with a real file or directory.
- **`tracker.specIds`** — team default id scheme for new specs when a tracker is configured. Parallel agents collide on bare `fn-N`; tracker-keyed ids (`WOR-17` → `wor-17-slug`; GitHub `#123` → `gh-123-slug`; GitLab iid → `gl-N-slug`) use the tracker as the distributed allocator. Enable: `flowctl config set tracker.specIds tracker` (or answer the setup question when a tracker is configured and the key is still unset). Details: [`tracker-sync.md`](tracker-sync.md) § Hybrid id model / `tracker.specIds`.

## Conventions

- **R17 cross-link discipline.** Each doc here is a self-contained reference. Canonical sources (`templates/spec.md`, `scripts/sync-codex.sh`, `STRATEGY.md`, `GLOSSARY.md`) are linked, never re-embedded.
- **Relative paths only.** No absolute `github.com/...` URLs anywhere in this tree — fork-survivable + offline-readable.
- **Length discipline.** Reference shape (tables, lists, schemas first; narrative second). Brevity beats completeness.

## See also

- [`../README.md`](../README.md) — plugin overview, install, workflow narrative.
- [`../../../STRATEGY.md`](../../../STRATEGY.md) — flow-next's strategic intent + active tracks.
- [`../../../GLOSSARY.md`](../../../GLOSSARY.md) — canonical vocabulary (Spec, Task, R-ID, ...).
- [`../../../CONTRIBUTING.md`](../../../CONTRIBUTING.md) — contributor entry point (local dev, adding skills, releasing).
- [`../../../CLAUDE.md`](../../../CLAUDE.md) — repo-level guide for working in this codebase.
